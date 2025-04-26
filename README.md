# Chatbot-Furia
Retirei a API Key (BEARER_TOKEN) Do Twitter por motivos de segurança.
E retirei a API Key do bot também (mesmo motivo)
:) 

Não sou tão bom comentando no codigo, então as vezes pedi pra Claude.ai comentar no codigo no meu lugar. :p


Erros de autenticação OAuth:

🔴 Não foi possível verificar o status da Twitch: {error_msg}
Exemplo: "🔴 Não foi possível verificar o status da Twitch: invalid client secret"


Erros na API de streams:

🔴 Erro ao acessar API da Twitch (Status {response.status_code})
Exemplo: "🔴 Erro ao acessar API da Twitch (Status 401)"


Exceções gerais:

⚠️ Erro ao verificar status da Twitch: {str(e)}
Exemplo: "⚠️ Erro ao verificar status da Twitch: Connection timeout"


Erro de configuração:

🔴 Configuração da Twitch incompleta (verifique .env)
Este é retornado na função status_twitch() quando as variáveis de ambiente estão ausentes


Quando não há transmissão ao vivo:

🔴 FURIA não está ao vivo no momento
