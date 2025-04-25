import os
import telebot
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import time
# Lembrete para depois usar também Schedule


# Caso alguem (ou ate eu mesmo) for mexer nisso no futuro, mantenha na ordem Numerica.

# 1° Carregar variáveis de ambiente (Pegar as API do .env)
load_dotenv() #.env (API'S Key)


# 2° Verifica variáveis ESSENCIAIS (Não mudar isso de posição) [Sempre depois do > load_dotenv] 
# Verificação melhorada
REQUIRED_ENVS = ["TELEGRAM_BOT_TOKEN", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET"]
missing_vars = [var for var in REQUIRED_ENVS if not os.getenv(var)]

if missing_vars:
    error_msg = (
        "🚨 Variáveis de ambiente obrigatórias faltando:\n"
        + "\n".join(f"- {var}" for var in missing_vars)
        + "\n\nℹ️ Adicione-as no arquivo .env"
    )
    raise ValueError(error_msg)

print("Variáveis carregadas:", {
    'TWITCH_CLIENT_ID': bool(os.getenv("TWITCH_CLIENT_ID")),
    'TWITCH_CLIENT_SECRET': bool(os.getenv("TWITCH_CLIENT_SECRET")),
    'LIQUIPEDIA_URLS': LIQUIPEDIA_PAGES
})

# 3° (Sempre o ultimo) Inicializar o bot do Telegram
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))

# URLs da Liquipedia para cada jogo
LIQUIPEDIA_PAGES = {
    'cs2': 'https://liquipedia.net/counterstrike/FURIA/Matches',
    'valorant': 'https://liquipedia.net/valorant/FURIA/Matches',
    'freefire': 'https://liquipedia.net/freefire/FURIA/Matches'
}

def log_erro(mensagem_erro):
    """Registra erros no console"""
    print(f"ERRO: {mensagem_erro}")

def verificar_twitch():
    """Verifica se a FURIA está ao vivo na Twitch"""
    try:
        client_id = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        
        # Obter token de acesso
        auth_url = "https://id.twitch.tv/oauth2/token"
        auth_params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        
        auth_response = requests.post(auth_url, params=auth_params)
        auth_data = auth_response.json()
        
        if 'access_token' not in auth_data:
            return "🔴 Não foi possível verificar o status da Twitch"
        
        access_token = auth_data['access_token']
        
        # Verificar stream
        headers = {
            'Client-ID': client_id,
            'Authorization': f'Bearer {access_token}'
        }
        
        stream_url = "https://api.twitch.tv/helix/streams"
        params = {'user_login': 'furiatv'}
        
        response = requests.get(stream_url, headers=headers, params=params)
        data = response.json()
        
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
        return "⚠️ Erro ao verificar status da Twitch"

def raspar_tweets_furia(quantidade=3):
    """Raspa os últimos tweets da FURIA via Nitter"""
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

def get_agenda_furia(jogo='valorant'):
    """Busca a agenda com múltiplos fallbacks"""
    try:
        # Verificar se o jogo é suportado
        if jogo not in LIQUIPEDIA_PAGES:
            return ["⚠️ Jogo não suportado. Use /agenda, /agenda_cs2 ou /agenda_ff"]
        
        # 1ª Tentativa: Scraping Liquipedia
        agenda = scrape_liquipedia(jogo)
        if agenda and "⚠️" not in agenda[0]:
            return agenda
        
        # 2ª Tentativa: API de Fallback
        agenda = get_agenda_esportscalendar(jogo)
        if agenda and "⚠️" not in agenda[0]:
            return agenda
        
        # 3ª Tentativa: Dados locais
        return get_agenda_local(jogo)
    
    except Exception as e:
        log_erro(f"Erro geral em get_agenda_furia: {str(e)}")
        return ["⚠️ Temporariamente indisponível. Tente /noticias"]

def scrape_liquipedia(jogo):
    """Scraping robusto com tratamento de erros"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Referer': 'https://www.google.com/'
        }
        
        response = requests.get(
            LIQUIPEDIA_PAGES[jogo],
            headers=headers,
            timeout=10,
            cookies={'skipmobile': '1'}
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
        
        return [f"⚠️ Erro {response.status_code} ao acessar"]
    
    except Exception as e:
        log_erro(f"Erro scraping Liquipedia: {str(e)}")
        return ["⚠️ Erro temporário"]

def get_agenda_esportscalendar(jogo):
    """Fallback para API alternativa"""
    try:
        # Exemplo com API fictícia - substitua por uma API real
        response = requests.get(
            f"https://api.esportscalendar.com/v3/{jogo}/furia",
            headers={'Authorization': f"Bearer {os.getenv('ESPORTS_CALENDAR_KEY')}"},
            timeout=8
        )
        
        if response.status_code == 200:
            data = response.json()
            return [
                f"🏆 {item['event']}\n"
                f"⚔️ FURIA vs {item['opponent']}\n"
                f"⏰ {item['date']}"
                for item in data[:3]
            ]
        
        return ["⚠️ API secundária indisponível"]
    
    except Exception as e:
        log_erro(f"Erro API fallback: {str(e)}")
        return []

def get_agenda_local(jogo):
    """Dados locais de fallback"""
    agendas = {
        'cs2': [
            "🏆 BLAST Premier\n⚔️ FURIA vs Vitality\n⏰ 25/07 20:00 BRT",
            "🏆 IEM Cologne\n⚔️ FURIA vs NAVI\n⏰ 28/07 18:00 BRT"
        ],
        'valorant': [
            "🏆 VCT Americas\n⚔️ FURIA vs LOUD\n⏰ 30/07 19:00 BRT"
        ],
        'freefire': [
            "🏆 Free Fire Pro League\n⚔️ FURIA vs LOUD\n⏰ 15/08 16:00 BRT"
        ]
    }
    return agendas.get(jogo, ["📅 Agenda não disponível para este jogo"])

# Comandos do bot
@bot.message_handler(commands=['start', 'ajuda', 'help'])
def menu_principal(message):
    """Menu de ajuda completo"""
    ajuda_msg = """
🐆 *BOT OFICIAL DA FURIA* 🔥

📋 *Comandos disponíveis:*
/noticias - Últimos tweets do time
/agenda - Próximos jogos (Valorant)
/agenda_cs2 - Próximos jogos de CS2
/agenda_ff - Próximos jogos de Free Fire
/redes - Todos os links de redes sociais
/twitch - Ver se está ao vivo
/loja - Loja oficial de produtos
/elenco - Jogadores do time

🔧 *Sugestões?* @IkarusRK
"""
    bot.reply_to(message, ajuda_msg, parse_mode='Markdown')

@bot.message_handler(commands=['noticias'])
def enviar_tweets(message):
    """Envia os últimos tweets"""
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
    """Mostra agenda de Valorant"""
    mostrar_agenda(message, 'valorant')

@bot.message_handler(commands=['agenda_cs2'])
def agenda_cs2(message):
    """Mostra agenda de CS2"""
    mostrar_agenda(message, 'cs2')

@bot.message_handler(commands=['agenda_ff'])
def agenda_freefire(message):
    """Mostra agenda de Free Fire"""
    mostrar_agenda(message, 'freefire')

def mostrar_agenda(message, jogo):
    """Função base para mostrar agenda"""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        jogos = get_agenda_furia(jogo)
        
        nomes_jogos = {
            'cs2': 'Counter-Strike 2',
            'valorant': 'Valorant',
            'freefire': 'Free Fire'
        }
        
        resposta = (
            f"📅 *Próximos Jogos de {nomes_jogos.get(jogo, 'Valorant')}* 🐆\n\n" +
            "\n\n".join(jogos) +
            f"\n\n🔗 [Ver todos no Liquipedia]({LIQUIPEDIA_PAGES[jogo]})"
        )
        
        bot.reply_to(message, resposta, parse_mode='Markdown')
        
    except Exception as e:
        log_erro(f"Erro /agenda_{jogo}: {str(e)}")
        bot.reply_to(message, "⚠️ Falha ao buscar agenda. Tente mais tarde.")

@bot.message_handler(commands=['redes'])
def mostrar_redes(message):
    """Mostra todas as redes sociais"""
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
        # Verifica se as credenciais existem
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
    """Link para a loja"""
    bot.send_message(
        message.chat.id,
        "🛒 *Loja Oficial da FURIA*:\n\n[Compre agora produtos oficiais](https://www.furia.gg/produtos)",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['elenco'])
def mostrar_elenco(message):
    """Mostra o elenco atual"""
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

# Loop principal
if __name__ == "__main__":
    print("Bot da FURIA iniciado!")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        log_erro(f"Falha crítica: {str(e)}")
        time.sleep(30)