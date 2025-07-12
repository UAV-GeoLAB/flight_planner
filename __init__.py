def classFactory(iface):
    from .flight_planner_v1 import FlightPlannerPW
    return FlightPlannerPW(iface)
