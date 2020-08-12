## start
* start
  - utter_welcome_msg
  - utter_ask_help
  - action_today_schedule

## greet
* greet
  - utter_greet

## ask schedule for today
* ask_schedule
  - action_today_schedule

##  ask route
* ask_route
  - action_check_destination
  - slot{"location":"Hysan Place"}
* inform{"location":"Hysan Place"}
  - slot{"location":"Hysan Place"}
  - action_route_plan
  - slot{"link":"https://maps.google.com?saddr=22.318284800000004,114.1604352&daddr=22.27981135,114.18378511861296"}
  - action_suggest
  - action_reset_event_slots

## ask route 2
* ask_route{"location":"Pacific Place"}
  - action_route_plan
  - slot{"link":"https://maps.google.com?saddr=22.318284800000004,114.1604352&daddr=22.277243849999998,114.16538264423335"}
  - action_suggest
  - action_reset_event_slots

## weather
* ask weather
  - action_get_weather
  - slot{"current_w": 29.1}
  - slot{"desc_w":"clear sky"}
  - action_weather_report

## ask covid 1
* ask_covid_cases
  - utter_covid_case
  - slot{"district":"kowloon city"}
* district{"district":"kowloon city"}
  - action_covid

## ask restaurant
* ask_restaurant
  - utter_ask_radius
* tell_radius {"radius": "500"}
  - action_search_restaurant
  - action_suggest_rest
  
## event create path 1
* greet
  - utter_greet
* request_create_event
  - utter_more_info
  - event_form
  - form{"name": "event_form"}
  - form{"name": null}
  - utter_confirm_schedule_details
> check_asked_schedule_details

## event create path 2
* greet
  - utter_greet
* inform{"location":" Lan Kwai Fong","time":"2020-08-07T19:00:00.000+08:00"}
  - event_form
  - form{"name": "event_form"}
  - slot{"location":"isquare"}
  - slot{"summary":"dinner at isquare"}
  - slot{"requested_slot":"time"}
  - form{"name": null}
  - utter_confirm_schedule_details
> check_asked_schedule_details

## user confirm details + event created 
> check_asked_schedule_details
* affirm
  - action_create_event
  - slot{"success":"success"}
  - action_set_reminder
  - action_route_plan
  - action_suggest
  - action_copy_slot
  - action_reset_event_slots

## user confirm details + overlapping event 
> check_asked_schedule_details
* affirm
  - action_create_event
  - slot{"success":"fail"}
  - utter_reschedule
* affirm
  - utter_ask_time
* inform{"time":"2020-08-07T20:00:00.000+08:00"}
  - slot{"time":"2020-08-07T20:00:00+08:00"}
  - event_form
  - slot{"time":"2020-08-07T20:00:00"}
  - slot{"end_time":"2020-08-07T20:00:00"}
  - form{"name":null}
  - slot{"requested_slot":null}
  - utter_confirm_schedule_details
> check_asked_schedule_details

## user deny details
> check_asked_schedule_details
* deny
  - utter_ask_again
  - action_deactivate_form
  - action_reset_event_slots
  - event_form
  - form{"name": "event_form"}
  - form{"name": null}
  - utter_confirm_schedule_details
> check_asked_schedule_details
  
## event create - summary + location
* request_create_event{"time":"2020-08-07T00:00:00.000+08:00"}
  - slot{"time":"2020-08-07T00:00:00.000+08:00"}
  - utter_more_info
  - event_form
  - form{"name":"event_form"}
  - slot{"requested_slot":"summary"}
* inform{"location":"isquare"}
  - slot{"location":"isquare"}
  - event_form
  - slot{"location":"isquare"}
  - slot{"summary":"dinner at isquare"}
  - slot{"requested_slot":"time"}
* inform{"time":"Aug 9 at 9pm"}
  - slot{"time":"Aug 9 at 9pm"}
  - event_form
  - slot{"time":"2020-08-09T21:00:00"}
  - slot{"end_time":"2020-08-09T22:00:00"}
  - form{"name":null}
  - slot{"requested_slot":null}
  - utter_confirm_schedule_details
> check_asked_schedule_details

## event create - summary + time
* request_create_event
  - utter_more_info
  - event_form
  - form{"name":"event_form"}
  - slot{"requested_slot":"summary"}
* inform{"location":"hyatt place"}
  - slot{"location":"hyatt place"}
  - event_form
  - slot{"location":"hyatt place"}
  - slot{"summary":"team building"}
  - slot{"requested_slot":"time"}
* inform{"time":"Aug 25 at 9pm"}
  - slot{"time":"Aug 25 at 9pm"}
  - event_form
  - slot{"time":"2020-08-25T21:00:00"}
  - slot{"end_time":"2020-08-25T22:00:00"}
  - form{"name":null}
  - slot{"requested_slot":null}
  - utter_confirm_schedule_details
  > check_asked_schedule_details

## overlapping event + affirm details later
* inform{"summary":"family dinner","location":"isquare","time":"2020-08-07T19:00:00.000+08:00"}
  - event_form
  - form{"name":"event_form"}
  - slot{"location":"isquare"}
  - utter_confirm_schedule_details
* affirm
  - action_create_event
  - slot{"success":"fail"}
  - utter_reschedule
* affirm
  - utter_ask_time
* inform{"time":"2020-08-07T21:00:00.000+08:00"}
  - event_form
  - form{"name":"event_form"}
  - slot{"summary":"family dinner"}
  - utter_confirm_schedule_details
* affirm
  - action_create_event
  - slot{"success":"success"}
  - action_set_reminder
  - action_route_plan
  - action_suggest
  - action_copy_slot
  - action_reset_event_slots

## utter_reschedule + deny
  - utter_reschedule
* deny
  - utter_anything_else
  - action_deactivate_form
  - form{"name": null}

## form + chitchat
* request_create_event
  - utter_more_info
  - event_form
  - form{"name": "event_form"}
* chitchat
  - respond_chitchat
  - event_form
  - form{"name": null}
  - slot{"requested_slot":null}
  - utter_confirm_schedule_details
> check_asked_schedule_details

## form + stop
* request_create_event
  - utter_more_info
  - event_form
  - form{"name": "event_form"}
* stop
  - utter_ask_continue
* deny
  - utter_anything_else
  - action_deactivate_form
  - form{"name": null}
  - action_reset_event_slots


## Some question from chitchat
* chitchat
  - respond_chitchat
    
## say thank you
* thank_you
  - utter_you_are_welcome

## say goodbye
* goodbye
  - utter_goodbye
