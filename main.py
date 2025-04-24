import os
import telebot
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import schedule
import time

# Pegar as API .env
load_dotenv()

# Ativar bot
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))

def log_erro(mensagem_erro):
    # Log erro
    print(f"ERRO: {mensagem_erro}")

# --- FUNÇÕES DE SCRAPING ---
def raspar_tweets_furia(quantidade=3):
    # Raspa os últimos tweets da FURIA via Nitter
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
                    div_texto = tweet.select_one('.tweet-content')
                    texto = div_texto.get_text(strip=True) if div_texto else "[Texto não disponível]"
                    
                    tag_data = tweet.select_one('.tweet-date a')
                    data = tag_data['title'] if tag_data else ""
                    tweet_link = f"https://twitter.com{tag_data['href']}" if tag_data else ""
                    
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

# --- funcao das api
def verificar_twitch():
    # Verifica se a FURIA está ao vivo na Twitch
    try:
        headers = {
            "Client-ID": os.getenv("TWITCH_CLIENT_ID"),
            "Authorization": f"Bearer {os.getenv('TWITCH_TOKEN')}"
        }
        response = requests.get(
            "https://api.twitch.tv/helix/streams",
            params={"user_login": "furiatv"},
            headers=headers,
            timeout=10
        )
        data = response.json()
        
        if data.get('data'):
            stream = data['data'][0]
            return (
                f"🔴 *AO VIVO NA TWITCH*:\n"
                f"🎮 {stream['title']}\n"
                f"👁️ {stream['viewer_count']} espectadores\n"
                f"📺 [Assistir agora](https://twitch.tv/furiatv)"
            )
        return "📻 A FURIA não está ao vivo no Twitch no momento"
    except Exception as e:
        log_erro(f"Erro Twitch API: {str(e)}")
        return "⚠️ Não foi possível verificar o status da Twitch"

# --- comandos bot
@bot.message_handler(commands=['start', 'ajuda', 'help'])
def menu_principal(message):
    # Menu de ajuda completo
    ajuda_msg = """
🐆 *BOT OFICIAL DA FURIA* 🔥

📋 *Comandos disponíveis:*
/noticias - Últimos tweets do time
/redes - Todos os links de redes sociais
/twitch - Ver se está ao vivo
/loja - Loja oficial de produtos
/agenda - Próximos jogos agendados
/elenco - Jogadores do time

🔧 *Sugestões?* @seuusername
"""
    bot.reply_to(message, ajuda_msg, parse_mode='Markdown')

@bot.message_handler(commands=['noticias'])
def enviar_tweets(message):
    # Envia os ultimos tws
    try:
        mensagem_temp = bot.reply_to(message, "🔄 Buscando últimas atualizações...")
        tweets = raspar_tweets_furia(3)
        
        resposta = "🐆 *Últimos Tweets da FURIA:*\n\n" + "\n\n━━━━━━━━\n\n".join(tweets)
        bot.edit_message_text(
            resposta,
            chat_id=mensagem_temp.chat.id,
            message_id=mensagem_temp.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        log_erro(f"Erro em /noticias: {str(e)}")
        bot.reply_to(message, "⚠️ Falha ao buscar tweets. Tente mais tarde.")

@bot.message_handler(commands=['redes'])
def mostrar_redes(message):
    # Mostra todas as redes sociais
    redes_msg = """
🌐 *REDES SOCIAIS OFICIAIS*:

📸 [Instagram](https://www.instagram.com/furiagg)
🐦 [X (Twitter)](https://x.com/FURIA)
🎮 [Twitch](https://www.twitch.tv/furiatv)
📹 [YouTube](https://youtube.com/@FURIAgg)
🛒 [Loja Oficial](https://www.furia.gg/produtos)
"""
    bot.send_message(
        message.chat.id,
        redes_msg,
        parse_mode='Markdown',
        disable_web_page_preview=False
    )

@bot.message_handler(commands=['twitch'])
def status_twitch(message):
    # Verifica status da Twitch
    bot.send_chat_action(message.chat.id, 'typing')
    status = verificar_twitch()
    bot.reply_to(message, status, parse_mode='Markdown')

@bot.message_handler(commands=['loja'])
def loja_oficial(message):
    # Link para a loja
    bot.send_message(
        message.chat.id,
        "🛒 *Loja Oficial da FURIA*:\n\n[Compre agora produtos oficiais](https://www.furia.gg/produtos)",
        parse_mode='Markdown'
    )

# --- LOOP PRINCIPAL ---
if __name__ == "__main__":
    print("Bot da FURIA iniciado!")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        log_erro(f"Falha crítica: {str(e)}")
        time.sleep(30)