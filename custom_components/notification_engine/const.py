"""Constants for the Notification Engine integration."""

DOMAIN = "notification_engine"
EVENTS_FILENAME = "notification_engine_events.json"

SERVICE_CREATE_EVENT = "create_event"
SERVICE_LIST_EVENTS = "list_events"
SERVICE_PROCESS_EVENTS = "process_events"
SERVICE_SEND_INFO = "send_info"
SERVICE_DELETE_EVENT = "delete_event"
SERVICE_PURGE_EVENTS = "purge_events"

CONF_PEOPLE = "people"
CONF_PEOPLE_ENTITIES = "people_entities"
CONF_AWAY_REMINDER_MODE = "away_reminder_mode"
CONF_AWAY_REMINDER_TOLERANCE_M = "away_reminder_tolerance_m"
CONF_AWAY_REMINDER_MAX_DISTANCE_M = "away_reminder_max_distance_m"
CONF_INSTALL_DASHBOARD = "install_dashboard"

DEFAULT_AWAY_REMINDER_MODE = "all"
DEFAULT_AWAY_REMINDER_TOLERANCE_M = 1000.0
DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M = 10000.0
DEFAULT_INSTALL_DASHBOARD = False
