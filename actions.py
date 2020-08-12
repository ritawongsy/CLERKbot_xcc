from typing import Any, Text, Dict, List, Union, Optional
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction
from datetime import datetime, timedelta,date
import dateutil
import requests
import json
import pickle
import os.path
import pytz
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from rasa_sdk.events import ReminderScheduled, ReminderCancelled
import geopandas
import geopy
import geocoder
from geopy. geocoders import Nominatim
from timefhuman import timefhuman
from rasa_sdk.events import AllSlotsReset


class EventForm(FormAction):

    def name(self) -> Text:
        return "event_form"

    @staticmethod
    def required_slots(tracker: Tracker) -> List[Text]:
        return ["summary", "time", "location",]
    
    def slot_mappings(self) -> Dict[Text, Union[Dict, List[Dict]]]:
        return {"summary": [self.from_entity(entity="summary"),
                            self.from_text(intent=["inform", "request_create_event"]),
                            ],
                "time": self.from_entity(entity="time"),
                "location": [self.from_entity(entity="location"),
                             self.from_text(intent=["inform", "request_create_event"]),
                            ],          
                }
    
    def validate_time(self,value: Text,
                  dispatcher: CollectingDispatcher,tracker: Tracker,
                  domain: Dict[Text, Any],) -> Optional[Text]:

        try:
            dateutil.parser.parse(value)
            if isinstance(value, dict):
                if value["to"] == value["from"]:
                    print("1")
                    dispatcher.utter_message(template="utter_wrong_time")
                    return{"time":None, "end_time":None}
                else:
                    end_time_value= value["to"]
                    end_time_obj = dateutil.parser.parse(end_time_value)
                    end_time= (end_time_obj - timedelta(hours=1)).isoformat()
                    
                    start_time_value=value['from']
                    start_time_obj = dateutil.parser.parse(start_time_value)
                    start_time = start_time_obj.isoformat()
                    print("2")
                    return {'time': start_time,'end_time': end_time}
            else:
                datetime_obj = dateutil.parser.parse(value)
                start_time = datetime_obj.isoformat()
                end_time= (datetime_obj + timedelta(hours=1)).isoformat()
                print("3")
                return {'time': start_time,'end_time':end_time}
        except:
            try:
                timefhuman(value)
                if type(timefhuman(value)) is datetime:
                    start_time = timefhuman(value).isoformat()
                    end_time = (start_time + timedelta(hours=1)).isoformat()
                    print("4")
                    return{"time":start_time, "end_time":end_time}
                elif type(timefhuman(value)) is tuple:
                    if timefhuman(value)[0] > timefhuman(value)[1]:
                        dispatcher.utter_message(template="utter_wrong_time")
                        print("5")
                        return{"time":None, "end_time":None}
                    else:
                        start_time = (list(timefhuman(value))[0]).isoformat()
                        end_time = (list(timefhuman(value))[1]).isoformat()
                        print("6")
                        return{"time":start_time, "end_time":end_time}
                else:
                    dispatcher.utter_message(template="utter_wrong_time")
                    print("7")
                    return{"time":None, "end_time":None}
            except:
                print("8")
                dispatcher.utter_message(template="utter_wrong_time")
                return{"time":None, "end_time":None}

    def submit(self,dispatcher: CollectingDispatcher,
        tracker: Tracker,domain: Dict[Text, Any],) -> List[Dict]:
        
        time = tracker.get_slot("time")
        end_time = tracker.get_slot("end_time")
        summary = tracker.get_slot("summary")
        location = tracker.get_slot("location")
        
        time_show = time[0:10] + " " + time[11:16]
        endtime_show = end_time[0:10] + " " + end_time[11:16]

        # utter submit template
        dispatcher.utter_message(text=f"I am going to schedule an event using the following parameters:\n - summary:{summary}\n - start: {time_show}\n - end: {endtime_show}\n - location: {location}")
        return []


class ActionCreateEvent(Action):
    def name(self):
        return 'action_create_event'

    def run(self, dispatcher, tracker, domain):
        time = tracker.get_slot("time")
        end_time_ori = tracker.get_slot("end_time")
        start_time = dateutil.parser.parse(tracker.get_slot("time"))
        end_time = dateutil.parser.parse(tracker.get_slot("end_time"))
        summary = tracker.get_slot("summary")
        location = tracker.get_slot("location")
        success = None
        
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = None

        if os.path.exists('token.pkl'):
            with open('token.pkl', 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pkl', 'wb') as token:
                pickle.dump(creds, token)

        # Call the Calendar API
        service = build('calendar', 'v3', credentials=creds)
        primary = (service.calendarList().list().execute())["items"][0]["id"]


        # Check the availibility of the time
        utc = pytz.utc
        timeMin = start_time
        timeMax = end_time
        min_utc = timeMin.astimezone(utc)
        max_utc = timeMax.astimezone(utc)
        
        body = {
        "timeMin": min_utc.isoformat(),
        "timeMax": max_utc.isoformat(),
        "items": [
            {
            "id": "primary"
            }
        ],
        "timeZone": "Asia/Hong_Kong"
            }
        
        freebusy = service.freebusy().query(body=body).execute()
        busy_dict = freebusy['calendars']
        for x in busy_dict:
            if len(busy_dict[x]["busy"])>0:
                success = "fail"
                dispatcher.utter_message(template="utter_time_conflicts")
                return [SlotSet("success", success), SlotSet("time", None),SlotSet("end_time", None)]
            else: 
                #Create event for the requested time period
                try:
                    event = {
                    'summary': summary,
                    'location': location,
                    'start': {
                        'dateTime': start_time.isoformat(),
                        'timeZone': 'Asia/Hong_Kong',
                    },
                    'end': {
                        'dateTime': end_time.isoformat(),
                        'timeZone': 'Asia/Hong_Kong',
                    },
                    }
                    
                    added_event = service.events().insert(calendarId='primary', body=event).execute()
                    event_link = added_event.get('htmlLink')
                    success = "success"
                    dispatcher.utter_message(text=f"Event Created. \n{event_link}")
                except:
                    dispatcher.utter_message(text="Error: Unable to create event.")
                return [SlotSet("success", success), SlotSet("time", time),SlotSet("end_time", end_time_ori),SlotSet("summary", summary),
                SlotSet("location", location)]


#### This class is the event reminder part####
class ActionSetReminder(Action):
    def name(self) -> Text:
        return "action_set_reminder"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        success = tracker.get_slot("success")
        if success == "success":
            dispatcher.utter_message("I will remind you 2 hours before the event start.")

            start_time = dateutil.parser.parse(tracker.get_slot("time"))
            reminder_time = start_time + timedelta(hours=-2)

            reminder = ReminderScheduled(
                "EXTERNAL_reminder",
                trigger_date_time=reminder_time,
                name="my_reminder",
                kill_on_user_message=False,
            )
            return [reminder]
        elif success == "fail":
            return[]

class ActionReactToReminder(Action):
    """Reminds the user to call someone."""

    def name(self) -> Text:
        return "action_react_to_reminder"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        summary = tracker.get_slot("summary_2")
        dispatcher.utter_message(f"Hey! You have {summary} in 2 hours later.")
        return []


class ActionResetEventSlots(Action):
    def name(self):
        return "action_reset_event_slots"

    def run(self, dispatcher, tracker, domain):
        start_time = tracker.get_slot("time")
        end_time = tracker.get_slot("end_time")
        summary = tracker.get_slot("summary")
        location = tracker.get_slot("location")
        success = tracker.get_slot("success")
        return [SlotSet("time", None),SlotSet("end_time", None),SlotSet("summary", None),SlotSet("location", None), SlotSet("success", None)]


#### This class is the schedule for today part.####
class ActionTodaySchedule(Action):
    def name(self):
        return 'action_today_schedule'

    def run(seld,dispatcher,tracker,domain):
        # import calendar
        creds = pickle.load(open("token.pkl","rb"))
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        service = build('calendar', 'v3', credentials=creds)
        primary = (service.calendarList().list().execute())["items"][0]["id"]

        # time in utc timeformat
        today = date.today()
        timeMin = datetime.combine(today, datetime.min.time())
        timeMax = datetime.combine(today, datetime.max.time())
        utc = pytz.utc
        min_utc = timeMin.astimezone(utc).isoformat()
        max_utc = timeMax.astimezone(utc).isoformat()

        #get the list of today's event
        list_allday=[]
        list_session=[]
        events= service.events().list(calendarId='primary',timeMin=min_utc, 
                timeMax=max_utc, singleEvents=True, orderBy='startTime').execute()
        for event in events["items"]:
            if "dateTime" in event["start"]:
                time = event["start"]["dateTime"]
                summary = event["summary"]
                session = {"start": time, "summary":summary}
                list_session.append(session)
            elif "date" in event["start"]:
                time = event["start"]["date"]
                summary = event["summary"]
                allday = {"start": time, "summary":summary}
                list_allday.append(allday)

        #print the list of schedule
        list_today=[]
        for i in list_allday:
            summary=i["summary"]
            list_today.append("All-day - " + summary)
        for i in list_session:
            start = (i["start"])[11:16]
            summary=i["summary"]
            list_today.append(start + " - " + summary)
        if len(list_today)==0:
            dispatcher.utter_message(text="You have no events scheduled today.\n Have a good day!:)")
        elif len(list_today)>0:
            dispatcher.utter_message(text="Here is your schedule for today:\n" + "\n".join(p for p in list_today))
        return[]


#### This class is the transportation part!####
class ActionRoutePlan(Action):
    def name(self):
        return 'action_route_plan'

    def run(self,dispatcher,tracker,domain):  
        if tracker.get_slot('success') == "fail":
            return[]
        elif tracker.get_slot('success') == "success" or tracker.get_slot('success') == None:
            print("routeplanstart") 
            endpoint = 'https://maps.googleapis.com/maps/api/directions/json?region=hk&'
            api_key = 'AIzaSyCtP9l7ye9ACQpAoYtr54P1lhj-Prt2NT0'

            # Get user's current location
            get_origin = requests.post(
            "https://www.googleapis.com/geolocation/v1/geolocate?key=AIzaSyCtP9l7ye9ACQpAoYtr54P1lhj-Prt2NT0").json()
            origin_lat = get_origin['location']['lat']
            origin_lng = get_origin['location']['lng']
            origin =  "{},{}".format(origin_lat,origin_lng)

            # Setup destination
            destination = str(tracker.get_slot('location'))
            print("get locatin slot")
            print(f"destination={destination}")

            locator = Nominatim(user_agent='myGeocoder')
            location_d = locator.geocode(destination +',Hong Kong')
            d_long = location_d.longitude
            d_lat = location_d.latitude
            dest = "{},{}".format(d_lat,d_long)
            
            # Print the link to google map with user's current location and destination
            link = 'https://maps.google.com?saddr=' + origin + '&daddr=' + dest

            return [SlotSet('link',link),SlotSet('origin_lat',origin_lat),SlotSet('origin_lng',origin_lng),
            SlotSet('destination',destination),SlotSet('origin',origin),SlotSet('dest',dest)]

###This is the route plan suggest part
class ActionSuggest(Action):
    def name(self):
        return 'action_suggest'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        #dispatcher.utter_message(text='You can reach ' + str(tracker.get_slot('location') + ' by driving, public transit, or walking'))
        if tracker.get_slot('success') == "fail":
            return[]
        elif tracker.get_slot('success') == "success" or tracker.get_slot('success') == None: 
            dispatcher.utter_message(template="utter_map_link")
            return []

###This is the get weather class
class ActionGetWeather(Action):
    def name(self):
        return 'action_get_weather'

    def run(self,dispatcher,tracker,domain):
        # Get user's current location
        get_origin = requests.post(
        "https://www.googleapis.com/geolocation/v1/geolocate?key=AIzaSyCtP9l7ye9ACQpAoYtr54P1lhj-Prt2NT0").json()
        origin_lat = get_origin['location']['lat']
        origin_lng = get_origin['location']['lng']


        api_key = "85a20dc653dfb8e0fbeede6ac23fdc07"
        w_url = "https://api.openweathermap.org/data/2.5/onecall?lat=%s&lon=%s&appid=%s&units=metric"%(origin_lat,origin_lng,api_key)
        weather_response = requests.get(w_url)
        weather = json.loads(weather_response.text)
        
        # Get current temperature in Celsius and description
        current_w = "{:.1f}".format(weather['current']['temp'])
        desc_w = weather['current']['weather'][0]['description']
        
        # Get hourly forecast
        count = 0
        forecast = []
        hourly = weather['hourly']
        for entry in hourly:
            if count <10:
                dt = datetime.fromtimestamp(entry["dt"])
                dt = dt.time().strftime('%H:%M')
                hour = entry['weather'][0]['description']
                temp = entry["temp"]
                forecast.append(str(dt) +"  " + str("{:.1f}".format(temp)) + "celsius  " + str(hour))
                count += 1

        return [SlotSet('current_w',current_w),SlotSet('desc_w',desc_w),SlotSet('forecast',forecast)]

###This is the weather report part
class ActionWeatherReport(Action):
    def name(self):
        return 'action_weather_report'
    
    def run(self,dispatcher,tracker,domain):
        dispatcher.utter_message(text='It is currently ' + str(tracker.get_slot('current_w')) + 'celsius.')
        dispatcher.utter_message(text='\n'.join([i for i in tracker.get_slot('forecast')]))
        return []

###This is the COVID part
class ActionCovidCases(Action):
    def name(self):
        return "action_covid"
    def run(self,dispatcher,tracker,domain):
        dist = tracker.get_slot("district")
        response = requests.get("https://api.data.gov.hk/v2/filter?q=%7B%22resource%22%3A%22http%3A%2F%2Fwww.chp.gov.hk%2Ffiles%2Fmisc%2Fbuilding_list_eng.csv%22%2C%22section%22%3A1%2C%22format%22%3A%22json%22%2C%22sorts%22%3A%5B%5B1%2C%22asc%22%5D%5D%7D").json()
        districts=[]
        for d in response:
            districts.append(d['District'])
        result = districts.count('{}'.format(dist))
        building = [response[i]['Building name'] for i in range(len(response)) if response[i]['District'] == dist]       
        dispatcher.utter_message(text= "Buildings with confirmed cases:\n" + '\n'.join([i for i in building]))
        dispatcher.utter_message(text= "There are "+ str(result) + " cases in " + str(dist) +".\n Please see the details above.")
        return[]

###This is the restaurant nearby part
class ActionSearchRestaurant(Action):
    def name(self):
        return 'action_search_restaurant'
    def run(self,dispatcher,tracker,domain): 
        ## The codes below are already in actionRoutePlan, can use tracker.get_slot for origin_lat,origin_lng
        api_key = "AIzaSyCtP9l7ye9ACQpAoYtr54P1lhj-Prt2NT0"  
        get_origin = requests.post(
        "https://www.googleapis.com/geolocation/v1/geolocate?key=AIzaSyCtP9l7ye9ACQpAoYtr54P1lhj-Prt2NT0").json()
        origin_lat = get_origin['location']['lat']
        origin_lng = get_origin['location']['lng']

        ## Need to copy codes below
        radius = str(tracker.get_slot('number'))
        place = requests.get('https://maps.googleapis.com/maps/api/place/nearbysearch/json?&type=restaurant&location={},{}&radius={}&key={}'.format
                            (origin_lat, origin_lng, radius, api_key)
                            ).json()
        rest_nearby = []
        count = 0
        rest_res = place['results']
        for i in rest_res:
            if count < 4:
                name = i['name']
                address = i['vicinity']
                rating = i['rating']
                rest_nearby.append(str(name)+ '\nRating: ' + str(rating) + '\nAddress: ' + str(address) )
                count += 1 
        print(rest_nearby)
        return [SlotSet('radius',radius),SlotSet('rest_nearby',rest_nearby)]

class ActionSuggestRest(Action):
    def name(self):
        return 'action_suggest_rest'

    def run(self,dispatcher,tracker,domain):
        dispatcher.utter_message(text="Here is what I found:")
        dispatcher.utter_message(text='\n \n'.join([ i for i in tracker.get_slot('rest_nearby')]))
        return[]

class Actioncopyslot(Action):
    def name(self):
        return 'action_copy_slot'

    def run(self,dispatcher,tracker,domain):
        start_time = tracker.get_slot("time")
        end_time = tracker.get_slot("end_time")
        summary = tracker.get_slot("summary")
        location = tracker.get_slot("location")
        return [SlotSet('time_2',start_time),SlotSet('end_time_2',end_time), SlotSet('summary_2',summary), SlotSet('location_2',location)]

class ActionCheckDestination(Action):
    def name(self):
        return 'action_check_destination'

    def run(self,dispatcher,tracker,domain):
        if tracker.get_slot('location')==None:
            dispatcher.utter_message(template="utter_ask_location")
        return []
