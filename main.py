import os
import telebot
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import time

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar o bot do Telegram
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))

def log_erro(mensagem_erro):
    """Registra erros no console"""
    print(f"ERRO: {mensagem_erro}")

def raspar_tweets_furia(quantidade=3):
    """Raspa os últimos tweets da FURIA"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9"
        }
        
        # Usando o Nitter (alternativa ao Twitter que permite scraping)
        resposta = requests.get(
            "https://nitter.net/FURIA",
            headers=headers,
            timeout=15
        )
        
        if resposta.status_code == 200:
            sopa = BeautifulSoup(resposta.text, 'html.parser')
            tweets = []
            
            # Extrai os cards de tweet
            for tweet in sopa.select('.tweet-body')[:quantidade]:
                try:
                    # Pega o texto do tweet
                    div_texto = tweet.select_one('.tweet-content')
                    texto = div_texto.get_text(strip=True) if div_texto else "[Texto não disponível]"
                    
                    # Pega a data do tweet
                    tag_data = tweet.select_one('.tweet-date a')
                    data = tag_data['title'] if tag_data else ""
                    
                    # Pega mídia (imagens) se disponível
                    midias = []
                    tags_midia = tweet.select('.attachment image')
                    for img in tags_midia:
                        if img.has_attr('src'):
                            midias.append(f"https://nitter.net{img['src']}")
                    
                    tweet_formatado = f"📅 {data}\n{texto}"
                    if midias:
                        tweet_formatado += f"\n🖼️ {midias[0]}"  # Mostra apenas a primeira imagem
                    
                    tweets.append(tweet_formatado)
                
                except Exception as e:
                    log_erro(f"Erro ao analisar tweet: {str(e)}")
                    continue
            
            return tweets if tweets else ["⚠️ Nenhum tweet encontrado. A estrutura da página pode ter mudado."]
        
        return [f"❌ Erro ao acessar página (HTTP {resposta.status_code})"]
    
    except Exception as e:
        log_erro(f"Erro no scraping: {str(e)}")
        return ["⚠️ Erro temporário. Tente novamente mais tarde."]

@bot.message_handler(commands=['start', 'ajuda'])
def enviar_boas_vindas(message):
    """Envia mensagem de boas-vindas"""
    mensagem = """
🔥 Bem-vindo ao Bot da FURIA! 🔥

Comandos disponíveis:
/noticias - Últimos tweets da FURIA
"""
    bot.reply_to(message, mensagem)

@bot.message_handler(commands=['noticias'])
def enviar_tweets(message):
    """Envia os tweets raspados"""
    try:
        # Envia mensagem de carregamento
        mensagem_temp = bot.reply_to(message, "🔄 Buscando últimas atualizações da FURIA...")
        
        # Pega os tweets
        tweets = raspar_tweets_furia(3)
        
        # Formata a resposta
        if tweets and not tweets[0].startswith("⚠️") and not tweets[0].startswith("❌"):
            resposta = "🐆 Últimas Atualizações da FURIA:\n\n" + "\n\n━━━━━━━━\n\n".join(tweets)
        else:
            resposta = tweets[0] if tweets else "❌ Falha ao buscar atualizações"
        
        # Edita a mensagem de carregamento com os resultados
        bot.edit_message_text(
            resposta,
            chat_id=mensagem_temp.chat.id,
            message_id=mensagem_temp.message_id
        )
    
    except Exception as e:
        log_erro(f"Erro no comando: {str(e)}")
        bot.reply_to(message, "⚠️ Ocorreu um erro. Por favor, tente novamente mais tarde.")

# Tratamento de comandos desconhecidos
@bot.message_handler(func=lambda message: True)
def comando_desconhecido(message):
    """Lida com comandos não reconhecidos"""
    bot.reply_to(message, "❌ Comando não reconhecido. Use /ajuda para ver os comandos disponíveis.")

# Loop principal
if __name__ == "__main__":
    print("Bot da FURIA iniciado no modo scraping!")
    while True:
        try:
            bot.polling(none_stop=True, interval=1)
        except Exception as e:
            log_erro(f"Bot crashou: {str(e)}")
            time.sleep(10)
            print("Reiniciando bot...")
