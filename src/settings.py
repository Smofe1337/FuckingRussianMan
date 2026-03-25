# all the tuneable knobs live here — touch .env only for tokens nothing else
# change whatever u want nobody will stop u

# ollama — local llm that does the heavy lifting
OLLAMA_MODEL    = 'llama3'
OLLAMA_URL      = 'http://localhost:11434'
EMBED_MODEL     = 'nomic-embed-text'

# storage paths — dont move db without updating this
DB_PATH         = 'database.db'
CHROMA_PATH     = './chroma_db'

# auto-posting default interval in hours — 0 kills it entirely
AUTO_POST_HOURS = 0.1

# how many examples we shove into the prompt — more = smarter but slower
RAG_EXAMPLES_CHAT = 30
RAG_EXAMPLES_POST = 40

# max tokens ollama spits out per request — keep chat short posts longer
CHAT_NUM_PREDICT = 50
POST_NUM_PREDICT = 180

# typing delay — makes the bot feel less like a robot and more like u
MIN_TYPING_DELAY  = 3
MAX_TYPING_DELAY  = 7
WORDS_PER_SECOND  = 0.4
MAX_SEND_DELAY    = 20

# how many turns of history we keep — trim this if ram is crying
MAX_HISTORY = 20

# random double space between words — makes it look authentically typed by a human
DOUBLE_SPACE_PROB = 0.25

# your user id — owner gets the admin panel and error dms
OWNER_ID = 7191689788

# chat where the bot replies as u
TARGET_CHAT = -1002083559827

# channel to learn from and post to — bot reads this eats it and learns
LEARN_CHANNEL = -1001917653138

# chats where userbot replies as the real account — add more if needed
USERBOT_CHATS = [-1002083559827]

# debug mode — true = log spam heaven false = only the shit that matters
DEBUG = True
