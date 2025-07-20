from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import time
import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  # Load from .env
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Load from .env
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')  # Load from .env

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Initialize OpenAI client
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

# Define system prompt and user prompt
# system_prompt = "You are an assistant that engages in extremely thorough, self-questioning reasoning. Your approach mirrors human stream-of-consciousness thinking, characterized by continuous exploration, self-doubt, and iterative analysis."
system_prompt = ""
prompt = "Provide detailed takeaways relevant to search keyword. Don't use words like 'transcript/video/author says' etc. Search keyword: "
summary_prompt = "Provide detailed takeaways. Don't use words like 'transcript/video/author says' etc. "

# Function to search for videos
def search_videos(keyword, max_results):
    request = youtube.search().list(q=keyword, part='id,snippet', maxResults=max_results)
    response = request.execute()
    return [(item['id']['videoId'], item['snippet']['title']) for item in response['items'] if item['id']['kind'] == 'youtube#video']

# Function to get transcript for a video
def get_transcript(video_id):
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return ' '.join([entry['text'] for entry in transcript])

# Function to split text into chunks
def split_text_into_chunks(text, max_tokens=int(os.getenv('MAX_TOKENS'))):
    words = text.split()  # Split text into words
    chunks = []
    current_chunk = []

    for word in words:
        current_chunk.append(word)
        if len(' '.join(current_chunk)) >= max_tokens:
            chunks.append(' '.join(current_chunk[:-1]))
            current_chunk = [word]

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

# Function to summarize text
def summarize_text(text):
    response = client.chat.completions.create(
        model=os.getenv('MODEL'),
        messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": text}],
        max_tokens=4096
    )
    if response.choices and len(response.choices) > 0:
        return response.choices[0].message.content.strip()
    return "No summary available."

# Streamlit app
def main():
    st.title("YouTube Topic Research / Video Summarizer")
    search_keyword = st.text_input("Enter a search keyword:")
    max_results = st.number_input("Number of videos to fetch:", min_value=1, max_value=50, value=5)
    youtube_link = st.text_input("OR Enter a YouTube link:")

    if st.button("Summarize"):
        if youtube_link:
            video_id = youtube_link.split("v=")[-1]
            try:
                transcript = get_transcript(video_id)
                chunks = split_text_into_chunks(transcript)
                summaries = []
                for chunk in chunks:
                    summary = summarize_text(summary_prompt + " transcript: " + chunk)
                    summaries.append(summary)
                st.write("\n".join(summaries))
            except Exception as e:
                st.write(f"Error fetching transcript for the video: {e}")
        elif search_keyword:
            videos = search_videos(search_keyword, max_results) 
            for video_id, title in videos:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                st.write(f"[{video_id}]({video_url})")
                try:
                    transcript = get_transcript(video_id)
                    chunks = split_text_into_chunks(transcript)
                    summaries = []
                    for chunk in chunks:
                        summary = summarize_text(prompt + search_keyword + " title: " + title + " transcript: " + chunk)
                        summaries.append(summary)
                    st.write("\n".join(summaries))
                except Exception as e:
                    st.write(f"Error fetching transcript for {title}: {e}")
                time.sleep(5)
        else:
            st.write("Please enter a search keyword.")

if __name__ == "__main__":
    main()