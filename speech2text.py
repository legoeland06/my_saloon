import speech_recognition

def record_voice()->list|None:
	microphone = speech_recognition.Recognizer()

	with speech_recognition.Microphone(
    chunk_size = 1024) as live_phone:
		microphone.adjust_for_ambient_noise(live_phone, duration=.5)

		print("je t'écoute: ")
		audio = microphone.listen(live_phone)
		try:
			phrase = microphone.recognize_google(audio, language='fr-FR')
			return phrase
		except speech_recognition.UnknownValueError:
			return None

def main():
	return record_voice()
if __name__ == '__main__':
	main()
	
