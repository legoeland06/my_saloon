"""
This module provides functionality to read and translate text from the system clipboard using the Gemini API and text-to-speech synthesis.

Classes:
    Recipe (BaseModel): A class used to represent a Recipe with a response attribute.

Functions:
    get_clipboard_text() -> str:

    translate_it(text_to_translate: str | list, target: str = "français(FR)") -> str:

    prepare_to_read(text: str, target: str) -> list:

    lancer(text: str = str(), langue: str = "français(FR)"):
        Launches the reading of the provided text using text-to-speech synthesis.
"""

from argparse import Namespace
import pyperclip
import pyttsx3
from google import genai
from secret import GEMINI_API_KEY
from pydantic import BaseModel
from colorama import Fore, Style
import os


class Recipe(BaseModel):
    """
    A class used to represent a Recipe.

    Attributes
    ----------
    response : str
        A string containing the response or description of the recipe.
    """

    response: str


def get_clipboard_text():
    """
    Retrieves the current text content from the system clipboard.

    Returns:
        str: The text content currently stored in the clipboard.
    """
    # Get the text from the clipboard
    # Check if the clipboard is empty
    if pyperclip.paste().strip() == str():
        print(Fore.RED + "Le presse-papiers est vide." + Style.RESET_ALL)
        lancer(text="Le presse-papiers est vide, vous devez d'abord Copier le texte à lire dans le presse-papiers ", langue="français(FR)")
        exit(0)

    return pyperclip.paste()


def translate_it(
    text_to_translate: str | list[str], target: str = "français(FR)"
) -> str:
    """
    Translates the given text to the specified target language using the Gemini API.
    Args:
        text_to_translate (str | list): The text to be translated. It can be a string or a list of strings.
        target (str): The target language for translation. Default is "français(FR)".
    Returns:
        str: The translated text.
    Raises:
        Exception: If there is an error with the translation API request.
    """
    if isinstance(text_to_translate,list) and text_to_translate.__len__() == 0:
        return str()

    if isinstance(text_to_translate,str) and text_to_translate.strip().__len__() == 0:
        return str()
    

    reformat_translated = (
        nettoyer_texte(text_to_translate)
        if isinstance(text_to_translate, str)
        else nettoyer_texte("\n".join(text_to_translate))
    )

    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=reformat_translated
        + "\nRépond au format : {'response':[la traduction]}"
        + f", en faisant une traduction fidèle [en {target} exclusivement] de ce texte.",
        config={
            "response_mime_type": "application/json",
            "response_schema": Recipe,
            "temperature": 0.2,
        },
        
    )
    casted_response = response.parsed.model_dump()["response"]  
    return casted_response or str()

def nettoyer_texte(text: str):
    """
    Nettoie le texte en supprimant les caractères indésirables et les lignes vides.
    Args:
        text (str): Le texte à nettoyer.
    Returns:
        list: Le texte nettoyé.
    """
    _ =text.replace("*", " ").replace("--", " ").replace("+", " ").replace("=", " ").replace("#", " ").replace("|", " ").replace("/", " ").replace("\xa0", "").replace("\\", " ").replace(":", " ").replace("www", " ").replace("https", " ").replace("http", " ")
    return _

def prepare_to_read(text: str, target: str):
    """
    Prepares the text for reading by removing unwanted characters and lines, and translating it to the target language.
    Args:
        text (str): The text to be prepared for reading.
        target (str): The target language for the translation.
    Returns:
        list: The cleaned and translated text.
    """

    NEPASLIRE = "ne pas lire"
    SECRET = "secret"
    strip_list = [
        line for line in text.splitlines()
        if not (line.startswith((NEPASLIRE, SECRET, "// ")))
    ]

    # vérification de la suppression éventuelle de lignes non traitées
    diff_lenght = text.splitlines().__len__() - strip_list.__len__()
    if strip_list.__len__() != text.splitlines().__len__():
        print(f"Attention :  {diff_lenght} lignes n'ont pas été traitées.")


    # on supprime les lignes vides
    strip_list = [line for line in strip_list if line.strip()]

    translated_text = translate_it(text_to_translate=strip_list, target=target)
    if translated_text == str():
        return translated_text
    else:
        return translated_text.splitlines(keepends=False)


def lancer(text: str = str(), langue: str = "français(FR)"):
    """
    Lance la lecture du texte fourni à l'aide de la synthèse vocale.
    Args:
        text (str): Le texte à lire. Par défaut, une chaîne vide.
        langue (str): La langue cible pour la lecture. Par défaut, "français(FR)".
    Returns:
        None
    """
    _max_long = os.get_terminal_size().columns

    if not text:
        return
    _sortie = prepare_to_read(text=text, target=langue)
    if _sortie.__len__() == 0:
        print(Fore.RED + "prepare_to_read() : pas de texte à lire" + Style.RESET_ALL)
        return

    # illustration du texte à lire dans le terminal avec des couleurs
    print(Fore.GREEN +"Lecture en cours...\n"+ "*" * _max_long + Style.RESET_ALL)
    for element in _sortie:
        print(Fore.YELLOW + element + Style.RESET_ALL)
    print(Fore.GREEN + "*" * _max_long + "\n" + Style.RESET_ALL)

    lire_voix(_sortie)
    return(_sortie)

def lire_voix(_sortie):
    _voice = pyttsx3.Engine()
    _voice.setProperty("rate", 150)
    _voice.setProperty("volume", 0.9)
    _voice.say("".join(_sortie))
    _voice.runAndWait()
    


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create a ArcHydro schema")
    parser.add_argument(
        "-l", metavar="langue", required=False, help="la langue de la réponse"
    )
    parser.add_argument(
        "-t", metavar="text", required=False, help="le texte à lire"
    )

    parser.add_argument(
        "-f", metavar="file", required=False, help="le fichier texte à lire"
    )

    args: Namespace = parser.parse_args()
    if args.l:
        langue = args.l
    else:
        langue = "français(FR)"
    if args.t:
        text = args.t
    elif args.f:
        # Si un fichier texte est fourni, on le lit et on le traduit
        # en français par défaut
        with open(args.f, "r", encoding="utf-8") as file:
            # on récupère le texte du fichier par paragraphes
            text = file.read()
            text = text.splitlines(keepends=True)
            text = "\n".join(text)
            # on nettoie le texte
            text = nettoyer_texte(text)
            if text.__len__() == 0:
                print(Fore.RED + "Le fichier est vide." + Style.RESET_ALL)
                lancer(text="Le fichier est vide, vous devez d'abord Copier le texte à lire dans le presse-papiers ", langue="français(FR)")
            lancer(text=text, langue=langue)
            

         
        exit(0)
    else:
        # Si aucun texte n'est fourni, on le récupère depuis le presse-papiers
        # et on le traduit
        # en français par défaut
        text = get_clipboard_text()

    lancer(text=text, langue=langue)
