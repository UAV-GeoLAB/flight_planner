def classFactory(iface):
    from .flight_planner import FlightPlanner
    return FlightPlanner(iface)
