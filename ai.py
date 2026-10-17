import os
from gigachat import GigaChat
KEY = os.getenv("AI_TOKEN")
def chat(message):
    with GigaChat(
        base_url="https://api.giga.chat/v1",
        credentials= KEY,
        scope="GIGACHAT_API_PERS",
        verify_ssl_certs=False,
        model="GigaChat-3-Pro"
    ) as client:
        response = client.chat.create(message)
        return (response.messages[0].content[0].text)



# from gigachat import GigaChat

# with GigaChat(
#     base_url="https://api.giga.chat/v1",
#     credentials=key,
#     verify_ssl_certs=False
# ) as client:
#     models = client.get_models()
#     for model in models.data:
#         print(f"{model.id_} (owned_by={model.owned_by})")