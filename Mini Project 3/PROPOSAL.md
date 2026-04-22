## My Project Proposal

**What I'm building:** A Flask web application that takes user inputs of where they are in Boston, where they want to get to in Boston, and by what time they want to get there, and then generates an output of what time they should leave to get to their desired destination on time. The app will also provide the fasted public transit route to take along with an interactive map which shows how the user will get there.

**Why I chose this:** I chose this application because I struggle with getting places on time and I generally underestimate the jouney time. With this application, I can now figure out the exact time I need to leave by in order to get to my destination on time!

**Core features:**
- Contains a form where the user enters an origin, a destination, and a target arrival time
- Uses Geocoding for both addresses via Mapbox, finds the nearest subway stop for each location, and pulls live arrival predictions from the MBTA V3 API to figure out which train to take
- Provides a journey breakdown showing walk → wait → ride → walk, plus a clear "Leave by HH:MM" answer
- Provides an interactive Mapbox map showing origin, both T stops, and destination, colored by subway line
- Contains sensible fallbacks: transfer detection with a time penalty, a "just walk" suggestion when both ends share a stop, and clear warnings when no T stop is within range or no trains are running

**What I don't know yet:** 
- I don't know how to calculate a specific user's average walk time in order for my application to generate more accurate 'leave times'
- I don't know how to have the application push out real-time, automated train delays/changes updates to the user once they have already run the application
