import os
import telebot
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import schedule
import time

# carregar env API'S
load_dotenv()

# Inicializar o bot do Telegram
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))

def log_erro(mensagem_erro):
    # Registra erros no console
    print(f"ERRO: {mensagem_erro}")

def raspar_tweets_furia(quantidade=3):
    # Raspa os últimos tws da FURIA
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9"
        }
        
        response = requests.get(
            "https://nitter.net/FURIA",
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            sopa = BeautifulSoup(response.text, 'html.parser')
            tweets = []
            
            for tweet in sopa.select('.tweet-body')[:quantidade]:
                try:
                    # Texto do tw
                    div_texto = tweet.select_one('.tweet-content')
                    texto = div_texto.get_text(strip=True) if div_texto else "[Texto não disponível]"
                    
                    # Data
                    tag_data = tweet.select_one('.tweet-date a')
                    data = tag_data['title'] if tag_data else ""
                    
                    # Link do tw
                    tweet_link = ""
                    if tag_data and tag_data.has_attr('href'):
                        tweet_link = f"https://twitter.com{tag_data['href']}"
                    
                    # Link de midia (vídeo/imagem)
                    media_link = ""
                    media_tag = tweet.select_one('.attachment.video, .attachment.image')
                    if media_tag and media_tag.has_attr('href'):
                        media_link = f"\n🔗 Mídia: https://nitter.net{media_tag['href']}"
                    
                    tweet_formatado = f"📅 {data}\n{texto}"
                    if tweet_link:
                        tweet_formatado += f"\n\n🔗 Tweet original: {tweet_link}"
                    if media_link:
                        tweet_formatado += media_link
                    
                    tweets.append(tweet_formatado)
                
                except Exception as e:
                    log_erro(f"Erro ao analisar tweet: {str(e)}")
                    continue
            
            return tweets if tweets else ["⚠️ Nenhum tweet encontrado"]
        
        return [f"❌ Erro ao acessar página (HTTP {response.status_code})"]
    
    except Exception as e:
        log_erro(f"Erro no scraping: {str(e)}")
        return ["⚠️ Erro temporário. Tente novamente mais tarde."]

def enviar_atualizacoes():
    # Envia atualizações automáticas
    try:
        chat_id = "7092763342"  # Chat ID (Telegram)
        tweets = raspar_tweets_furia(3)
        
        if tweets:
            mensagem = "🐆 Atualização Automática da FURIA:\n\n" + "\n\n━━━━━━━━\n\n".join(tweets)
            bot.send_message(chat_id, mensagem)
    except Exception as e:
        log_erro(f"Erro no envio automático: {str(e)}")

# Comandos do bot
@bot.message_handler(commands=['start', 'ajuda'])
def enviar_boas_vindas(message):
    # Envia msg de boas-vindas
    bot.reply_to(message, "🔥 Bem-vindo ao Bot da FURIA! Use /noticias para os últimos tweets.")

@bot.message_handler(commands=['noticias'])
def enviar_tweets(message):
    # Envia os tw copiados
    try:
        mensagem_temp = bot.reply_to(message, "🔄 Buscando últimas atualizações...")
        tweets = raspar_tweets_furia(3)
        
        resposta = "🐆 Últimos tweets da FURIA:\n\n" + "\n\n━━━━━━━━\n\n".join(tweets) if tweets else "❌ Nenhum tweet encontrado"
        
        bot.edit_message_text(
            resposta,
            chat_id=mensagem_temp.chat.id,
            message_id=mensagem_temp.message_id
        )
    except Exception as e:
        log_erro(f"Erro no comando: {str(e)}")
        bot.reply_to(message, "⚠️ Ocorreu um erro. Tente novamente mais tarde.")

# Agendamento executa 1x/dia às 12:00 por causa do plano free
schedule.every().day.at("12:00").do(enviar_atualizacoes)

# Loop principal [pequeno loop pra ficar burlando o plano free, ele fica reiniciando o script para reiniciar a contagem das 24 horas]
if __name__ == "__main__":
    print("Bot da FURIA iniciado!")
    try:
        while True:
            schedule.run_pending()
            bot.polling(none_stop=True, interval=1)
            time.sleep(60)
    except Exception as e:
        log_erro(f"Bot crashou: {str(e)}")
        print("Reiniciando bot em 10 segundos...")
        time.sleep(10)