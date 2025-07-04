import asyncio
import threading
import time,os
import PyPDF2
import keyboard  # Ensure this is imported at the top of the file
from asyncio.log import logger
from tkinter import filedialog, messagebox
from colorama import Fore
from google import genai as gn
from secret import DEEPSEEK_API,GEMINI_API_KEY
from secret import GROQ_API_KEY
from openai import OpenAI
from groq import Groq



META_LLAMA = "meta-llama/llama-4"
NO_CONVERSATION_HISTORY="No conversation history available."
llms = [
    "qwen-qwq-32b",
    # f"{META_LLAMA}-scout-17e-instruct",
    # f"{META_LLAMA}-maverick-17b-128e-instruct",
    f"{META_LLAMA}-scout-17b-16e-instruct",
    "deepseek-reasoner",
    "deepseek-chat",
    "llama3-70b-8192",
    # "llama3-8b-8192",
    "gemma2-9b-it",
    ]

class LLMWorker:
    def __init__(self, model_name):
        self.model_name = model_name
        self.response = None
        self.stop_event = threading.Event()
        self.history = []

    def generate_response(self, prompt, shared_event, result_container):
        if not shared_event.is_set() and not self.stop_event.is_set():
            client = None
            if self.model_name == "deepseek-reasoner" or self.model_name == "deepseek-chat":
                client=OpenAI(api_key=DEEPSEEK_API, base_url="https://api.deepseek.com/v1", )
            if self.model_name == "llama3-70b-8192" or self.model_name == "meta-llama/llama-4-scout-17b-16e-instruct" \
                or self.model_name == "qwen-qwq-32b" or self.model_name == "Gemini-2.0" or self.model_name == "gemma2-9b-it"\
                    or self.model_name == "deepseek-r1-distill-llama-70b":
                client=Groq(api_key=GROQ_API_KEY)
            try:
                self.response=client.chat.completions.create(
                model=self.model_name,
                messages=[system_prompt,{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.25,
                top_p=0.9,
                stop=None,
                stream=False,
            )  
                result_container.append(self.response.choices[0].message)
            except Exception as e:
                print(Fore.RED+f"Erreur lors de l'appel à {self.model_name}: {e}"+Fore.RESET)
                result_container.append(f"Erreur: {e}")
            
            shared_event.set()  # Signale aux autres threads qu'une réponse est trouvée
            if self.stop_event.is_set():
                # print(Fore.RED+f"Arrêt demandé pour {self.model_name}"+Fore.RESET)
                return
            print("-----------------"+Fore.GREEN+f"\nRéponse de {self.model_name}"+Fore.RESET+"\n-----------------\n")



    def add_to_history(self, message):
        """Ajoute un message à l'historique."""
        self.history.append(message)
    def get_history(self,index_message):
        """Récupère l'historique jusqu'à un certain message."""
        return self.history[:index_message]

    def reset(self):
        """Réinitialise le worker pour une nouvelle session."""
        self.response = None
        self.stop_event.clear()

class MessageAi:
    def __init__(self, role, message):
        self.role = role
        self.message = message

    def __str__(self):
        return f"{self.role}: {self.message}"

    def __repr__(self):
        return f"{self.role}: {self.message}"
    
    def get_instance(self):
        """Retourne une instance de MessageAi."""
        return self
    
class Conversation:
    def __init__(self,question:MessageAi, answer:MessageAi,llmworker:LLMWorker,timestamp=None):
        self.timestamp = timestamp if timestamp else time.time()
        self.question = question
        self.answer = answer
        self.llmworker = llmworker

    def add_question(self, question:MessageAi):
        """Ajoute une question à la conversation."""
        self.question = question

    def add_answer(self, answer:MessageAi):
        """Ajoute une réponse à la conversation."""
        self.answer = answer

    def display_me(self):
        """Affiche la conversation."""
        print(f"Question: {self.question.message}")
        print(f"Answer: {self.answer.message}")
        print(f"Timestamp: {time.ctime(self.timestamp)}")
        print(f"LLM Worker: {self.llmworker.model_name}")

    def display_answer(self):
        """Affiche la réponse."""
        print(f"Answer: {self.answer.message}")

    def display_question(self):
        """Affiche la question."""
        print(f"Question: {self.question.message}")

class History:
    def __init__(self):
        self.content:list = []

    def add_conversation(self, conversation:Conversation):
        """Ajoute une conversation à l'historique."""
        self.content.append(conversation)

    def get_last_conversation(self)-> Conversation| None:
        """Récupère la dernière conversation."""
        if self.content:
            return self.content[-1]
        else:
            return None
    
    def get_conversation(self, index_message):
        """Récupère une conversation à un index donné."""
        if 0 <= index_message < len(self.content):
            return self.content[index_message]
        else:
            return None
        
    def get_all_conversations(self):
        """Récupère toutes les conversations."""
        return self.content
    
    def reset(self):
        """Réinitialise l'historique pour une nouvelle session."""
        self.content = []

    def history_to_text(self):
        sortie=str()
        for i, conv in enumerate(self.get_all_conversations(), start=0):
            # print(f"**************************\n{i+1}. {cv.question.content} \n -> {cv.answer.content}\n\n")
            if isinstance(conv,Conversation):
                sortie+=f"{i+1}. {conv.question.message} \n -> {conv.answer.message }\n\n"
        return sortie


def load_pdf(parent) -> str:
    try:
        file_to_read = filedialog.askopenfile(
            parent=parent,
            title="Ouvrir un fichier pdf",
            defaultextension="pdf",
            mode="r",
            initialdir=".",
        )
        print("Extraction du PDF...")
        if file_to_read is not None:
            resultat_txt = read_pdf(file_to_read.name)
            print("Fin de l'extraction")
        else:
            resultat_txt = "rien à lire, fichier vide"
            print(resultat_txt)

        return resultat_txt
    except Exception as _e:
        messagebox.Message("Problème avec ce fichier pdf")
        return "None"


def read_pdf(book: str):
    text = str()
    pdf_reader = PyPDF2.PdfReader(book)
    pages = pdf_reader.pages
    for page in pages:
        text += page.extract_text() + "\n"
    return text

def get_terminal_size():
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80  # Default fallback width

system_prompt = {"role": "system", "content": "you are a helpful french assistant. \
             if needed, work step by step.\n Never stop until you finish to answer completly. "}

def run_llm_competition(prompt, llm_workers):
    """
    Lance plusieurs LLM en concurrence et retourne la première réponse.
    Args:
        prompt: Le prompt à envoyer aux LLM.
        llm_workers: Liste des workers LLM initialisés.
    Returns:
        La première réponse obtenue.
    """
    shared_event = threading.Event()
    result_container = []  # Partagé entre les threads pour stocker la réponse

    threads = []
    from StoppableThread import StoppableThread
    for worker in llm_workers:
        worker.reset()
        thread = StoppableThread(
            name=f"Thread-{worker.model_name}",
            target=worker.generate_response,
            args=(prompt, shared_event, result_container))
        thread.start()
        threads.append(thread)

    # Attendre qu'une réponse soit trouvée
    shared_event.wait()

    # Stopper tous les autres workers
    for worker in llm_workers:
        worker.stop_event.set()

        
    mainthread = threading.main_thread()
    for thread in threading.enumerate():
        if thread != mainthread:
            thread.stop() if isinstance(thread, StoppableThread) else None
            

    # Attendre la fin propre des threads (optionnel)
    for thread in threads:
        thread.stop() if isinstance(thread, StoppableThread) else None
        del thread

    yield result_container[0].content if result_container[0] else "Aucune réponse"
def read_text_file(file) -> list:
    """lit le fichier text chargé est passé en paramètre"""
    with open(file, "r", encoding="utf-8") as file_to_read:
        content = file_to_read.readlines()
    return content

def load_txt(parent) -> str:
    """
    Ouvre une boite de dialogue pour charger un fichier texte,
    appelle la méthode de lecture qui renvois le résultat
    sous forme de liste et retourne cette liste reformattée sous
    forme de texte
    """
    error_msg = "Problème pour charger le fichier texte"
    try:
        file_to_read = filedialog.askopenfile(
            parent=parent,
            title="Ouvrir un fichier txt",
            defaultextension="txt",
            mode="r",
            initialdir=".",
        )
        if file_to_read != None:
            print(file_to_read.name)

            resultat_txt = read_text_file(file_to_read.name)

            # on prepare le text pour le présenter à la méthode insert_markdown
            # qui demande un texte fait de lignes séparées par des \n
            # transforme list[str] -> str
            resultat_reformater = str().join(resultat_txt)

            return resultat_reformater

    except Exception as e:
        messagebox.showerror(f"{error_msg}")
        logger.exception(msg=error_msg, exc_info=e)
        logger.error(f"{error_msg}")
    return error_msg


async def ask_for_save(text):
    necessite_enregistrement = Groq(api_key=GROQ_API_KEY).chat.completions.create(
        model="llama3-8b-8192",
        messages=[system_prompt,
                    {"role": "system", "content": """
                    You are a virtual assistant and you need to keep in memory some information from our exchanges for fluid and follow-up interactions.\
                    \n Important informations are:
                    \n - Personal informations
                    \n - All kind of lists
                    \n - All kind of code or implementation                    
                    \n - Date and time
                    \n - All the information that can be used to improve the conversation and the user experience
                    \n - all the information that not existe neither in my knowledge base nor in the conversation history
                    \n - information tagged as **important** by the user
                     

                     \n Not important informations are:
                    \n - All the information that already exist in my knowledge base or in the conversation history
                    \n - All the information from the assistant
                    
                    example 1: 
                    user : Do you think this information should be saved ? 'Bonjour''
                    assistant : 'no'
                    
                    example 2: 
                    user : Do you think this information should be saved ? 'Je suis un homme de 45 ans'
                    assistant : 'yes'
                    
                    example 3: 
                    user : Do you think this information should be saved ? 'Je suis un homme de 45 ans et je fais du vélo'
                    assistant : 'yes'
                    
                    example 3: 
                    user : Do you think this information should be saved ? 'donne moi la recette de la tarte aux pommes'
                    assistant : 'no'
                    
                    example 3: 
                    user : Do you think this information should be saved ? 'la date d'aujourd'hui est le 12 octobre 2023'
                    assistant : 'yes'
                     
                    \nOk ! Now you have to answer with only 'yes' or 'no' :\n
                    """},
                    {"role": "user", "content": f"Do you think this is something to keep as important ? {str(text)}"},],
        max_tokens=400,
        temperature=0.025,
        top_p=1,
        stop=None,
        stream=False,
    )
    _sortie:str= necessite_enregistrement.choices[0].message.content
    # print(_sortie)
    
    if "yes" in _sortie.lower() or "oui" in _sortie.lower():
        return True
    else:
        return False
    

async def make_resume(text):
    resumer = Groq(api_key=GROQ_API_KEY).chat.completions.create(
        model="llama3-8b-8192",
        messages=[system_prompt,
                    {"role": "system", "content": """
                    You are a virtual assistant.\
                    """},
                    {"role": "user", "content": f"récupère les informations dans le texte ci-dessous, et fais en un résumé clair et factuel: \n{str(text)}\
                     \n ne renvois que le résumé."},],
        max_tokens=2000,
        temperature=0.025,
        top_p=1,
        stop=None,
        stream=False,
    )
    _sortie:str= resumer.choices[0].message.content
    return _sortie

# Exemple d'utilisation
def print_status(llms, choice):
    print(Fore.YELLOW+"\nQuestion["+Fore.GREEN+f"{"all Ai" if not choice or choice=="0" else llms[int(choice)-1] }"+Fore.RESET+"]: (CTRL+ENTER) or help\n"+"="*get_terminal_size()+Fore.RESET+"\n")

def affiche_ai_list(llms):
    print(Fore.GREEN+"Liste des modèles disponibles:\n")
    for i, llm in enumerate(llms, start=1):
        print(f"\t{i}. {llm}")
    print(Fore.RESET)

def display_help():
    print(Fore.YELLOW+"Available commands:\n"+Fore.RESET)
    print("\t# 'loadtxt' - Load a text file.")
    print("\t# 'loadpdf' - Load a PDF file.")
    print("\t# 'clear' - Clear the screen.")
    print("\t# 'exit' - Exit the program.")
    print("\t# 'help' - Display this help message.")
    print("\t# 'setAI' - Set the AI model.")
    print("\t# 'history' - Display conversation history.")
    print("\t# 'last' - Display the last conversation.")
    print("\t# 'history_clear' - Clear the conversation history.")
    print()

def main():
    print(Fore.CYAN+"Welcome to the Equilibrium Chatbot!"+Fore.RESET)
    print("---------------------------------")
    print("Type 'help' to get a list of commands.")
    choice = None
    history=None
    # history_all= []
    while True:
        # Get user input in multiline format
        print_status(llms, choice)
        question = []
        while not keyboard.is_pressed("ctrl+enter"):
            try:
                line = input()
                question.append(line)
                if line.lower() == "help":
                    # Display help message
                    display_help()
                    print_status(llms, choice)
                if line.lower() == "loadtxt":
                    # Load a text file
                    question.append(load_txt(None)+"\n")
                if line.lower() == "loadpdf":
                    # Load a PDF file
                    question.append(load_pdf(None)+"\n")
                if line.lower() == "history_clear":
                    # Clear the conversation history
                    if history and isinstance(history,History):
                        history.reset()
                        print("Conversation history cleared.")
                    else:
                        print(NO_CONVERSATION_HISTORY)
                    print_status(llms, choice)
                if line.lower() == "history":
                    # Display conversation history
                    print(Fore.YELLOW+"Conversation History:\n"+Fore.RESET)
                    if history and isinstance(history,History):
                        print(history.history_to_text())
                    else:
                        print(NO_CONVERSATION_HISTORY)
                    print_status(llms, choice)

                if line.lower() == "last":
                    # Display the last conversation
                    last_conv = history.get_last_conversation()
                    if last_conv:
                        print(Fore.YELLOW+"Last Conversation:\n"+Fore.RESET)
                        print(f"Question: {last_conv.question.message}")
                        print(f"Answer: {last_conv.answer.message}")
                    else:
                        print(NO_CONVERSATION_HISTORY)
                    print_status(llms, choice)

                if line.lower() == "clear":
                    # Clear the screen
                    os.system("cls" if os.name == "nt" else "clear")
                    print_status(llms, choice)
                    # print(Fore.YELLOW+"\nQuestion: (CTRL+ENTER) or help\n"+"="*Terminal_width+Fore.RESET)
                    question = []
                if line == "setAI":
                    while True:
                        print(Fore.YELLOW+"Select AI model (1-5) or 0 for all:\n"+Fore.RESET)
                        affiche_ai_list(llms)
                        choice = input(f"Enter your choice (1-{len(llms)}): ")
                        if choice in [str(n) for n in range(1, len(llms)+1)]:
                            print(f"You selected option {choice}: {llms[int(choice)-1]}.")
                            print_status( llms, choice)
                            break
                        elif choice == "0":
                            print("You selected option 0: All models.")
                            print_status( llms, choice)
                            choice = None
                            break
                        else:
                            print("Invalid choice, please try again.")
                
                if line=="exit":
                    # Exit the program
                    print("Exiting the program.")
                    exit()
            except KeyboardInterrupt:
                print("\nExiting the program.")
                exit()
            except EOFError:
                break

       
        prompt = "\n".join(question)

        print(Fore.GREEN+"\nRéponse:\n"+"="*get_terminal_size()+Fore.RESET+"\n")
        init_timer = float(time.perf_counter_ns())
        print("patientez...\n", end="", flush=True)
        # Initialisation des workers (chaque worker représente un LLM différent)
        if choice:
            llm_workers = [
                LLMWorker(llms[int(choice)-1]),
            ]
        else:
            llm_workers = [
                LLMWorker(llm) for llm in llms
            ]
        
        if history and isinstance(history,History):
            result = run_llm_competition(history.history_to_text() +"\n"+prompt, llm_workers)
            elapsed_time = (time.perf_counter_ns() - init_timer)/10_000
        else:
            result = run_llm_competition(prompt, llm_workers)
            elapsed_time = (time.perf_counter_ns() - init_timer)/10_000

        # Affichage du résultat
        _result=str()
        if result is not None:
            _question=MessageAi(role="user", message=str())
            _answer=MessageAi(role="assistant", message=str())
            for element in result:
                print(element, end="", flush=True)
                _result+=str(element)
            print(Fore.GREEN+f"\n-------------------\nTemps total: {elapsed_time:.2f}s"+Fore.RESET)

            # ici on va se poser la question de la nécessité d'enregistrer cette conversation
            # pour cela on va poser la question au llm
            # save_prompt=asyncio.run(ask_for_save(text=prompt))
            # save_result=asyncio.run(ask_for_save(text=_result))
            # if save_prompt or save_result:
            #     print(Fore.YELLOW+"This prompt should be saved.\n"+Fore.RESET)
            #     # Enregistrement de la conversation dans l'historique
            #     if save_prompt:
            #         _question=MessageAi(role="user", message=asyncio.run(make_resume(prompt)))

            #     if save_result:
            #         _answer=MessageAi(role="assistant", message=asyncio.run(make_resume(_result)))

            #     # On ajoute la conversation à l'historique
            #     _llmworker=llm_workers[0]
            #     _conversation=Conversation(
            #         question=_question,
            #         answer=_answer,
            #         llmworker=_llmworker,
            #         timestamp=time.time()
            #     )
            #     if history is None or not isinstance(history, History):
            #         history = History()
            #     history.add_conversation(_conversation)
            
        # suzy= threading.main_thread()
        # del suzy
        


if __name__ == "__main__":
    main()
    