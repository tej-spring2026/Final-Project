## My Project Proposal: Earnings Call Sentiment Analyzer

**What I'm building:** An application that loads multiple earnings call transcipts from the same public company across consecutive quarters, analyzes text for potential shifts in language and sentiment over time, and visualizes whether tone became more cautious before/during underperforming quarters. 
**Why I chose this:** In my stock trading/research experiences, I've noticed that stock prices can fluctuate soely based on the confidence, language, and tone a CEO uses during earnings calls. I want to be able to use this tool to measure nervous or excitment sentiment patterns during company earnings calls so I can better trade around these stock catalysts. 
**Core features:**
- Creates and loads interactive folder given user inputs of earnings call transcript file paths and custom labels (e.g. "PLTR Q1 2025") 
- Cleans and normalizes text in transcipts
- Produces a sentiment score based on postive vs. negative language usage and hedge-word ratio (e.g 'we expect', 'we anticipate', 'roughly')
- Normalizes the sentiment score by word count for fair comparison across varying transcript lengths
- Prints a ranked comparison table showing which quarters had the most and least cautious language
**What I don't know yet:**
- Unclear on best transcript source I should have the user upload to ensure fast and accurate clean-up of raw transcript text (Deciding between Motley Fool, Insider Monkey, SeekingAlpha, or directly from company IR website)
- I'm also unsure on the sentiment measuring dictionary to use/create as finance words sometimes behave differently than everyday language words
- I'm not quite sure how I'll split up and weight the earnings call's prepared remarks section vs.  its Q&A section. Need to figure out which is more revealing of overall sentiment.
