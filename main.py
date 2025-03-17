from flask import Flask, request, jsonify, send_file
import subprocess
import io
from datetime import datetime

app = Flask(__name__)

def log(message):
    """Helper function to print messages with timestamps."""
    print(f"{datetime.now()}: {message}")

@app.route('/api/piper', methods=['POST'])
def piper_tts():
    """
    API endpoint to receive text, language, and speaker, and convert it to speech using Piper.
    Returns the audio file directly as a response.
    """
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Invalid request, 'text' field is required."}), 400
        
        text = data['text']
        language = data.get('language', 'ne_NP')  # Default to Nepali
        piper_speaker = data.get('piper_speaker', '0')  # Default to speaker 0
        output_format = data.get('format', 'wav')  # Default to WAV
        
        log(f"Text to convert: {text}")
        log(f"Language: {language}, Speaker: {piper_speaker}, Format: {output_format}")
        
        # Validate output format
        if output_format not in ['wav', 'mp3']:
            return jsonify({"error": "Invalid format. Supported formats: 'wav', 'mp3'."}), 400
            
        # Construct the Piper command
        command = [
            "piper",
            "--model", f"models/{language}-google-medium.onnx",
            "--speaker", piper_speaker,
            "--output_file", "-"  # Output to stdout
        ]
        
        log(f"Running Piper command: {' '.join(command)}")
        
        # Execute the Piper command - important: don't use text=True for binary data
        process = subprocess.run(
            command, 
            input=text.encode('utf-8'),  # Encode the input text
            capture_output=True          # Capture binary output
        )
        
        # Handle success or failure
        if process.returncode != 0:
            log(f"Error executing command. Return code: {process.returncode}")
            log(f"stderr: {process.stderr.decode('utf-8', errors='replace')}")
            return jsonify({"error": "Error executing Piper command.", "details": process.stderr.decode('utf-8', errors='replace')}), 500
        
        # Get binary audio data directly
        audio_data = process.stdout
        
        # Convert to MP3 if requested
        if output_format == 'mp3':
            log("Converting WAV to MP3...")
            try:
                # Use ffmpeg to convert WAV to MP3
                ffmpeg_command = [
                    "ffmpeg",
                    "-i", "pipe:0",  # Read from stdin
                    "-f", "mp3",      # Output format
                    "pipe:1"          # Write to stdout
                ]
                
                ffmpeg_process = subprocess.run(
                    ffmpeg_command,
                    input=audio_data,
                    capture_output=True
                )
                
                if ffmpeg_process.returncode != 0:
                    log(f"Error converting to MP3: {ffmpeg_process.stderr.decode('utf-8', errors='replace')}")
                    return jsonify({"error": "Error converting audio to MP3."}), 500
                    
                audio_data = ffmpeg_process.stdout
                
            except Exception as e:
                log(f"Error during MP3 conversion: {e}")
                return jsonify({"error": "Error converting audio to MP3."}), 500
        
        # Create an in-memory file-like object
        audio_file = io.BytesIO(audio_data)
        audio_file.seek(0)
        
        # Determine MIME type
        mime_type = f"audio/{output_format}"
        
        # Send the audio file as a response
        log("Audio generated successfully.")
        return send_file(
            audio_file,
            mimetype=mime_type,
            as_attachment=True,
            download_name=f"speech.{output_format}"
        )
        
    except Exception as e:
        log(f"An error occurred: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# Run the Flask application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)