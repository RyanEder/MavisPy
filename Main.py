import speech_recognition as sr
import pyglet
import time
from gtts import gTTS
import urllib
import simplejson
import geocoder

r = None
def Init():
    global r
    r = sr.Recognizer()
    r.energy_threshold = 200
    r.dynamic_energy_threshold = True
    r.dynamic_energy_adjustment_damping = 0.15
    r.pause_threshold = 0.15
    r.non_speaking_duration = 0.15
    pyglet.options['audio'] = ('openal', 'directsound', 'silent')

# Interactive Functions
class Audio:
    def __init__(self, r):
        self.recognizer = r
    def GetMicData(self, r, timeout):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = None
            while audio==None:
                try:
                    audio = self.recognizer.listen(source, timeout)
                except:
                    audio=None
        return audio

    def GetUserInput(self, timeout, surpress_output=False):
        try:
            return self.recognizer.recognize_google(self.GetMicData(self.recognizer, timeout)).lower()
        except:
            if not surpress_output: self.DidntUnderstand()
            return None

    def Speak(self, tts, timeout=0):
        tts.save("response.mp3")
        pyglet.resource.media("response.mp3").play()
        time.sleep(timeout)

    def DidntUnderstand(self):
        self.Speak(gTTS("I didn't understand you", lang='en'))

    def Repeater(self, text=None):
        if not text:
            text = self.GetUserInput(5)
            if not text: return
        self.Speak(gTTS(text, lang='en'))

# Data Gathering Functions
class Data:
    def GetIPAddress(self):
        response = urllib.request.urlopen('http://jsonip.com')
        try:
            return simplejson.loads(response.read())['ip']
        except:
            return None

    def GetLatLng(self, ip_address=None):
        if ip_address:
            return geocoder.ip(ip_address).latlng
        else:
            return geocoder.ip('me').latlng

class Weather:
    def __init__(self, a, d):
        self.audio = a
        self.data = d
        self.last_download = 0

    def PopulateWeather(self):
        if time.time() - self.last_download > 1800:
            self.last_download = time.time()
            self.latlng = self.data.GetLatLng()
            url = 'http://forecast.weather.gov/MapClick.php?&lat='+str(self.latlng[0])+'&lon='+str(self.latlng[1])+'&FcstType=dwml'
            self.weather = urllib.request.urlopen(url).read().decode('utf-8')
            self.location = self.weather.split('<description>')[1].split('</description>')[0].split(',')[0]
            return True
        return False

    def GetTemperature(self):
        self.PopulateWeather()
        temp = self.weather.split('temperature type="apparent"')[1].split('<value>')[1].split('</value>')[0]
        self.audio.Speak(gTTS(temp + " degrees Fahrenheit in " + self.location, lang='en'), 2)

    def GetHumidity(self):
        self.PopulateWeather()
        humidity = self.weather.split('humidity type="relative"')[1].split('<value>')[1].split('</value>')[0]
        self.audio.Speak(gTTS(humidity + " percent in " + self.location, lang='en'), 2)

    def GetWind(self):
        self.PopulateWeather()
        wind_sustained = self.weather.split('<wind-speed type="sustained"')[1].split('<value>')[1].split('</value>')[0]
        wind_gust = self.weather.split('<wind-speed type="gust"')[1].strip().split('<value>')[1].split('</value>')[0]
        self.audio.Speak(gTTS("Wind speeds in " + self.location + " are " + wind_sustained + "miles per hour, with gusts up to " + wind_gust + ".", lang='en'), 4)

    def GetForecast(self, day):
        if self.PopulateWeather():
            temp = self.weather.split('<time-layout time-coordinate="local"')[1].split('</layout-key>')[1].strip().split('</time-layout>')[0].strip().split('\n')
            sprites = [i.split('period-name=')[1].split('>')[0].split('"')[1].lower() for i in temp]
            self.tomorrow = sprites[2]
            temp = self.weather.split('<name>Text Forecast</name>')[1].strip().split('</wordedForecast>')[0].strip().split('\n')
            text_forecasts = [i.split('<text>')[1].strip().split('</text>')[0].strip().lower() for i in temp]
            if not len(sprites) == len(text_forecasts):
                self.audio.Speak(gTTS("I had a hard time retrieving the forecasts, try again later", lang='en'), 4)
                return

            self.forecast = {}
            for i in range(len(sprites)):
                self.forecast[sprites[i]] = text_forecasts[i]
        if not day in self.forecast:
            if day == 'this afternoon':
                day = 'tonight'
            elif day == 'tomorrow':
                day = self.tomorrow
            elif day == 'tomorrow night':
                day = self.tomorrow + ' night'

        if day in self.forecast:
            self.audio.Speak(gTTS(day + ", " + self.forecast[day], lang='en'), 7)
        else:
            self.audio.Speak(gTTS("I had a hard time retrieving the forecast for " + day, lang='en'), 4)

    last_download = 0
    weather = None
    forecast = None
    location = None
    latlng = None
    tomorrow = ''

# Dialogue Flow Functions
class Dialogue:
    def __init__(self, a, d, w):
        self.audio = a
        self.data = d
        self.weather = w
        self.conversation_state = "Initializing"

    def WakeLoop(self):
        while True:
            try:
                text = self.audio.GetUserInput(1, surpress_output=True)
                if 'avis' in text or 'arvis' in text:
                    if len(text.split(' ')) == 1 or self.Parser(base_text=text) == False:
                        self.audio.Speak(gTTS("Yes?", lang='en'))
                    while True:
                        if self.Parser() == False: break
                    break
            except:
                continue

    def Parser(self, base_text=None):
        repeater = False
        if not base_text:
            text = self.audio.GetUserInput(8, surpress_output=False)
            if not text: return False
        else: text = base_text

        # Weather based queries
        if (('temp' in text or 'temperature' in text) or
            (('hot' in text or 'cold' in text or 'like' in text) and 'out' in text and not
                ('monday' in text or 'tuesday' in text or 'wednesday' in text or 'thursday' in text or 'friday' in text or 'saturday' in text or 'sunday' in text or 'tomorrow' in text))):
            self.weather.GetTemperature()
        elif (('humidity' in text or 'humid' in text) and not
                ('monday' in text or 'tuesday' in text or 'wednesday' in text or 'thursday' in text or 'friday' in text or 'saturday' in text or 'sunday' in text or 'tomorrow' in text)):
            self.weather.GetHumidity()
        elif 'weather' in text or 'forecast' in text or 'out' in text:
            night = ''
            if 'night' in text: night = ' night'
            if 'tonight' in text: self.weather.GetForecast('tonight')
            elif 'tomorrow' in text: self.weather.GetForecast('tomorrow' + night)
            elif 'monday' in text: self.weather.GetForecast('monday' + night)
            elif 'tuesday' in text: self.weather.GetForecast('tuesday' + night)
            elif 'wednesday' in text: self.weather.GetForecast('wednesday' + night)
            elif 'thursday' in text: self.weather.GetForecast('thursday' + night)
            elif 'friday' in text: self.weather.GetForecast('friday' + night)
            elif 'saturday' in text: self.weather.GetForecast('saturday' + night)
            elif 'sunday' in text: self.weather.GetForecast('sunday' + night)
            else: self.weather.GetForecast('this afternoon')
        elif 'wind' in text:
            self.weather.GetWind()

        # End
        elif 'thank' in text:
            self.audio.Speak(gTTS("Very welcome.", lang='en'), 1)
            return False
        else: repeater = True

        # Have something to report now.
        if tts:
            self.audio.Speak(tts, talk_timeout)
            return True
        else: # Echo the input, we don't know what to do with it yet.
            if base_text: return False
            if repeater: self.audio.Repeater(text)
            return False

    conversation_state = "Off"

# Main
Init()
audio = Audio(r)
data = Data()
weather = Weather(audio, data)
dialogue = Dialogue(audio, data, weather)
while True:
    dialogue.WakeLoop()
time.sleep(3)
