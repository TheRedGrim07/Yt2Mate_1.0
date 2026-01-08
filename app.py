import os
from flask import Flask, render_template, request, send_file
import yt_dlp

app = Flask(__name__)

# 1. Create a folder to store videos temporarily
# If we don't do this, the app will crash when it tries to save the file.
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def get_video_info(url):
    # 'quiet': True means "Don't spam my terminal with text"
    ydl_opts = {'quiet': True, 'no_warnings': True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # CRITICAL: download=False means "Just look at it, don't download yet"
            info = ydl.extract_info(url, download=False)
            
            clean_formats = []
            
            # YouTube gives 50+ formats. We loop through them to find the good ones
                    
                # --- DEBUG FILTER ---
            for f in info.get('formats', []):
                
                # Filter 1: Accept MP4 OR WebM (YouTube loves WebM now)
                if f.get('ext') not in ['mp4', 'webm']:
                    continue
                
                # Filter 2: TEMPORARILY REMOVED AUDIO CHECK
                # Let's see silent videos too, just to prove it works.
                # if f.get('acodec') == 'none': continue <--- Commented out
                
                # Get filesize
                filesize = f.get('filesize')
                
                # If filesize is missing, estimate it (approx calculation)
                if not filesize:
                     filesize = f.get('filesize_approx')

                if filesize:
                    size_mb = round(filesize / (1024 * 1024), 2)
                    
                    # Add a label so we know if it has audio or not
                    has_audio = "🔇 Silent" if f.get('acodec') == 'none' else "🔊 Sound"
                    
                    clean_formats.append({
                        'format_id': f['format_id'],
                        'resolution': f.get('resolution', 'Unknown'),
                        'filesize': f"{size_mb} MB ({has_audio})", # Update this string
                        'ext': f.get('ext')
                    })

            # Return a neat dictionary to the frontend
            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration_string'),
                # Reverse so the highest quality (1080p) is at the top
                "formats": reversed(clean_formats), 
                "original_url": url
            }
    except Exception as e:
        print(f"Error: {e}")
        return None
    
# --- ROUTE 1: The Search Page ---
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # 1. Get the URL the user pasted
        url = request.form.get('url')
        
        # 2. Run our "Inspector" function
        video_data = get_video_info(url)
        
        if video_data:
            # 3. If found, show the "download.html" card
            return render_template('download.html', video=video_data)
        
        return "Error: Could not fetch video. Try a different link."
        
    # If it's a GET request (just opening the page), show the search bar
    return render_template('index.html')


# --- ROUTE 2: The Download Action ---
@app.route('/download_file', methods=['POST'])
def download_file():
    # 1. Get the data from the hidden form inputs
    url = request.form.get('url')
    format_id = request.form.get('format_id')
    
    # 2. Configure the downloader for the specific quality
    ydl_opts = {
        'format': format_id, # This ensures we get exactly 720p or 1080p
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 3. Actually download the file to the 'downloads' folder
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # 4. Send the file from the server to the user's browser
            return send_file(filename, as_attachment=True)
            
    except Exception as e:
        return f"Error Downloading: {e}"

if __name__ == '__main__':
    app.run(debug=True)