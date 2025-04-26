import os
import telebot
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import time

# Carregar variáveis de ambiente
load_dotenv()

# Verificação das variáveis obrigatórias
REQUIRED_ENVS = ["TELEGRAM_BOT_TOKEN", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET"]
missing_vars = [var for var in REQUIRED_ENVS if not os.getenv(var)]

if missing_vars:
    error_msg = (
        "🚨 Variáveis de ambiente obrigatórias faltando:\n"
        + "\n".join(f"- {var}" for var in missing_vars)
        + "\n\n Adicione no arquivo .env"
    )
    raise ValueError(error_msg)

# Inicializar o bot
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))

# URLs da Liquipedia
LIQUIPEDIA_PAGES = {
    'valorant': 'https://liquipedia.net/valorant/FURIA/Matches',
}

def log_erro(mensagem_erro):
    """Registra erros no console"""
    print(f"ERRO: {mensagem_erro}")

def verificar_twitch():
    """Verifica se a FURIA está ao vivo na Twitch."""
    try:
        client_id = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        
        print(f"Verificando Twitch com Client ID: {client_id[:5]}...")
        
        # Obter token de acesso
        auth_url = "https://id.twitch.tv/oauth2/token"
        auth_params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        
        auth_response = requests.post(auth_url, params=auth_params)
        auth_data = auth_response.json()
        
        print(f"Auth response status: {auth_response.status_code}")
        print(f"Auth data: {auth_data}")
        
        if 'access_token' not in auth_data:
            error_msg = auth_data.get('message', 'Sem mensagem de erro')
            print(f"Erro na autenticação: {error_msg}")
            return f"🔴 Não foi possível verificar o status da Twitch: {error_msg}"
        
        access_token = auth_data['access_token']
        
        # Verificar stream
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}'
        }
        
        stream_url = "https://api.twitch.tv/helix/streams"
        params = {'user_login': 'furiatv'}
        
        print("Enviando requisição para API de streams...")
        response = requests.get(stream_url, headers=headers, params=params)
        print(f"Stream response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Erro na API de streams: {response.text}")
            return f"🔴 Erro ao acessar API da Twitch (Status {response.status_code})"
        
        data = response.json()
        print(f"Stream data: {data}")
        
        if data.get('data'):
            stream = data['data'][0]
            return (
                f"🎮 *FURIA está AO VIVO na Twitch!*\n\n"
                f"📺 {stream['title']}\n"
                f"👀 {stream['viewer_count']} espectadores\n"
                f"🔗 https://www.twitch.tv/furiatv"
            )
        return "🔴 FURIA não está ao vivo no momento"
    
    except Exception as e:
        log_erro(f"Erro ao verificar Twitch: {str(e)}")
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return f"⚠️ Erro ao verificar status da Twitch: {str(e)}"

def raspar_tweets_furia(quantidade=3):
    """Raspa os últimos tweets da FURIA com tratamento de Markdown"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9"
        }
        
        response = requests.get("https://nitter.net/FURIA", headers=headers, timeout=15)
        
        if response.status_code == 200:
            sopa = BeautifulSoup(response.text, 'html.parser')
            tweets = []
            
            for tweet in sopa.select('.tweet-body')[:quantidade]:
                try:
                    # 1. Extrair texto básico
                    div_texto = tweet.select_one('.tweet-content')
                    texto = div_texto.get_text(strip=True) if div_texto else "[Texto não disponível]"
                    
                    # 2. Sanitizar Markdown (remove caracteres problemáticos)
                    texto = texto.replace("*", "★").replace("_", "⸻").replace("[", "(").replace("]", ")")
                    
                    # 3. Extrair metadados
                    tag_data = tweet.select_one('.tweet-date a')
                    data = tag_data['title'] if tag_data else ""
                    tweet_link = f"https://twitter.com{tag_data['href']}" if tag_data else ""
                    
                    # 4. Tratar mídia. As vezes o bot falha.
                    media_link = ""
                    media_tag = tweet.select_one('.attachment.video, .attachment.image')
                    if media_tag and media_tag.has_attr('href'):
                        media_link = f"\n🔗 Mídia: https://nitter.net{media_tag['href']}"
                    
                    # 5. Montar resposta com Markdown seguro
                    tweet_formatado = f"📅 *{data}*\n`{texto}`"
                    if tweet_link:
                        tweet_formatado += f"\n\n🔗 [Tweet original]({tweet_link})"
                    if media_link:
                        tweet_formatado += media_link.replace("*", "★")
                    
                    tweets.append(tweet_formatado)
                
                except Exception as e:
                    log_erro(f"Erro ao analisar tweet: {str(e)}")
                    continue
            
            return tweets if tweets else ["⚠️ Nenhum tweet encontrado"]
        
        return [f"❌ Erro ao acessar página (HTTP {response.status_code})"]
    
    except Exception as e:
        log_erro(f"Erro no scraping: {str(e)}")
        return ["⚠️ Erro temporário. Tente novamente mais tarde."]

def scrape_liquipedia(jogo):
    """Scraping da Liquipedia"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9'
        }
        
        response = requests.get(
            LIQUIPEDIA_PAGES[jogo],
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            matches = soup.find_all('div', class_='match', limit=5)
            
            jogos = []
            for match in matches:
                try:
                    tournament = match.find('div', class_='match-tournament').get_text(strip=True)
                    team1 = match.find('div', class_='team-left').get_text(strip=True)
                    team2 = match.find('div', class_='team-right').get_text(strip=True)
                    time = match.find('div', class_='match-time').get_text(strip=True)
                    
                    jogos.append(
                        f"🏆 {tournament}\n"
                        f"⚔️ {team1} vs {team2}\n"
                        f"⏰ {time} BRT\n"
                        f"━━━━━━━━"
                    )
                except AttributeError:
                    continue
            
            return jogos if jogos else ["📅 Nenhum jogo agendado"]
        
        return [f"⚠️ Erro {response.status_code} ao acessar Liquipedia"]
    
    except Exception as e:
        log_erro(f"Erro scraping Liquipedia: {str(e)}")
        return ["⚠️ Erro temporário"]

def get_agenda_local(jogo):
    """Dados locais de fallback"""
    agendas = {
        'valorant': [
            "🏆 VCT Americas\n⚔️ FURIA vs LOUD\n⏰ 30/07 19:00 BRT"
        ],
    }
    return agendas.get(jogo, ["📅 Agenda não disponível para este jogo"])

def get_agenda_furia(jogo='valorant'):
    """Busca a agenda com fallbacks"""
    try:
        if jogo not in LIQUIPEDIA_PAGES:
            return ["⚠️ Jogo não suportado"]
        
        # 1ª Tentativa: Liquipedia
        agenda = scrape_liquipedia(jogo)
        if agenda and "⚠️" not in agenda[0]:
            return agenda
        
        # 2ª Tentativa: Dados locais
        return get_agenda_local(jogo)
    
    except Exception as e:
        log_erro(f"Erro em get_agenda_furia: {str(e)}")
        return ["⚠️ Temporariamente indisponível"]

# Handlers
@bot.message_handler(commands=['start', 'ajuda', 'help'])
def menu_principal(message):
    ajuda_msg = """
🐆 *BOT OFICIAL DA FURIA* 🔥

📋 *Comandos disponíveis:*
/noticias - Últimos tweets do time
/agenda - Próximos jogos (Valorant)
/redes - Todos os links de redes sociais
/twitch - Ver se está ao vivo
/loja - Loja oficial de produtos
/elenco - Jogadores do time
"""
    bot.reply_to(message, ajuda_msg, parse_mode='Markdown')

@bot.message_handler(commands=['noticias'])
def enviar_tweets(message):
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

@bot.message_handler(commands=['agenda'])
def agenda_valorant(message):
    mostrar_agenda(message, 'valorant')

def mostrar_agenda(message, jogo):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        jogos = get_agenda_furia(jogo)
        
        nomes_jogos = {
            'valorant': 'Valorant',
        }
        
        resposta = (
            f"📅 *Próximos Jogos de {nomes_jogos.get(jogo, 'Valorant')}* 🐆\n\n" +
            "\n\n".join(jogos) +
            f"\n\n🔗 [Ver todos no Liquipedia]({LIQUIPEDIA_PAGES[jogo]})"
        )
        
        bot.reply_to(message, resposta, parse_mode='Markdown')
        
    except Exception as e:
        log_erro(f"Erro em /agenda_{jogo}: {str(e)}")
        bot.reply_to(message, f"⚠️ Falha ao buscar agenda de {jogo}")

@bot.message_handler(commands=['redes'])
def mostrar_redes(message):
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
    try:
        if not all([os.getenv("TWITCH_CLIENT_ID"), os.getenv("TWITCH_CLIENT_SECRET")]):
            return bot.reply_to(message, "🔴 Configuração da Twitch incompleta (verifique .env)")
        
        bot.send_chat_action(message.chat.id, 'typing')
        status = verificar_twitch()
        bot.reply_to(message, status, parse_mode='Markdown')
        
    except Exception as e:
        log_erro(f"Erro em /twitch: {str(e)}")
        bot.reply_to(message, "🔴 Erro temporário. Tente novamente mais tarde.")

@bot.message_handler(commands=['loja'])
def loja_oficial(message):
    bot.send_message(
        message.chat.id,
        "🛒 *Loja Oficial da FURIA*:\n\n[Compre agora produtos oficiais](https://www.furia.gg/produtos)",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['elenco'])
def mostrar_elenco(message):
    try:
        elenco = """
👥 *Elenco FURIA 2024*

*CS2:*
- KSCERATO 🇧🇷
- FalleN 🇧🇷
- chelo 🇧🇷
- arT 🇧🇷
- guerri (Técnico) 🇧🇷

*Valorant:*
- Khalil 🇧🇷
- mwzera 🇧🇷
- Qck 🇧🇷
- Mazin 🇧🇷
- fRoD (Técnico) 🇺🇸

🔗 [Detalhes completos](https://www.furia.gg/teams)
"""
        bot.reply_to(message, elenco, parse_mode='Markdown')
    except Exception as e:
        log_erro(f"Erro /elenco: {str(e)}")
        bot.reply_to(message, "⚠️ Falha ao carregar elenco")

# Iniciar o bot
print("🐆 Bot da FURIA iniciado!")
try:
    bot.polling(none_stop=True)
except Exception as e:
    log_erro(f"Falha crítica: {str(e)}")
    time.sleep(30)