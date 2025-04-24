import os
import telebot
import requests
import time
from dotenv import load_dotenv

#Vrum Vrum bot
bot = telebot.TeleBot(BOT_TOKEN)

def log_error(error_message):
    # Log de erros
    print(f"ERRO: {error_message}")
    # Da ate pra ser expandido para salvar em arquivo ou enviar alertas. 

def get_furia_user_id():
    # Puxar id furia do tw
    try:
        url = 'https://api.twitter.com/2/users/by/username/furiagg'
        headers = {'Authorization': f'Bearer {BEARER_TOKEN}'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'id' in data['data']:
                return data['data']['id']
            else:
                log_error("Estrutura de resposta inesperada ao obter ID do usuário")
                return None
        else:
            log_error(f"Erro ao buscar ID do usuário: {response.status_code}")
            return None
    except Exception as e:
        log_error(f"Exceção ao buscar ID do usuário: {str(e)}")
        return None

def get_latest_tweets(user_id, count=5):
    # Buscar tw recentes da furia
    try:
        url = f'https://api.twitter.com/2/users/{user_id}/tweets'
        headers = {'Authorization': f'Bearer {BEARER_TOKEN}'}
        params = {'max_results': count, 'tweet.fields': 'created_at,text'}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                return [tweet['text'] for tweet in data['data']]
            else:
                log_error("Nenhum tweet encontrado na resposta")
                return []
        else:
            log_error(f"Erro ao buscar tweets: {response.status_code}")
            return []
    except Exception as e:
        log_error(f"Exceção ao buscar tweets: {str(e)}")
        return []

@bot.message_handler(commands=['start'])
def start_command(message):
    #CMD inicio
    welcome_msg = """
🔥 Bem-vindo(a) ao Bot da FURIA! 🔥

Use /help para ver os comandos disponíveis.
"""
    bot.reply_to(message, welcome_msg)

@bot.message_handler(commands=['help'])
def help_command(message):

# ==========

    #CMD ajuda
    comandos = """
👋 Bem-vindo(a) ao Bot da FURIA!

📋 Comandos disponíveis:
/help - Mostra esta mensagem de ajuda.
/noticias - Exibe os últimos tweets da FURIA.

Mais comandos em breve!
"""
    bot.reply_to(message, comandos)

@bot.message_handler(commands=['noticias'])
def noticias(message):
    """Busca e envia as últimas notícias da FURIA"""
    # Enviar mensagem de carregamento
    wait_message = bot.reply_to(message, "⏳ Buscando as últimas notícias da FURIA...")
    
    # Buscar ID do usuário
    user_id = get_furia_user_id()
    
    if user_id:
        # Buscar tweets
        tweets = get_latest_tweets(user_id)
        
        if tweets:
            resposta = "\n\n---\n\n".join(tweets)
            bot.edit_message_text(
                f"🗞️ Últimos tweets da FURIA:\n\n{resposta}", 
                chat_id=wait_message.chat.id, 
                message_id=wait_message.message_id
            )
        else:
            bot.edit_message_text(
                "Não encontrei tweets recentes da FURIA. Tente novamente mais tarde.", 
                chat_id=wait_message.chat.id, 
                message_id=wait_message.message_id
            )
    else:
        bot.edit_message_text(
            "❌ Erro ao buscar informações da FURIA. Tente novamente mais tarde.", 
            chat_id=wait_message.chat.id, 
            message_id=wait_message.message_id
        )

# Lidar com mensagens não reconhecidas
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Comando não reconhecido. Use /help para ver os comandos disponíveis.")

if __name__ == "__main__":
    print("Bot da FURIA iniciado!")
    # Usar polling seguro com tratamento de exceções
    while True:
        try:
            bot.polling(none_stop=True, interval=1)
        except Exception as e:
            log_error(f"Erro no polling: {str(e)}")
            time.sleep(5)  # Esperar antes de tentar novamente
