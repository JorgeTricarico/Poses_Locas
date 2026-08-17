import wave
import struct
import math
import random

def generate_beat(filename):
    sample_rate = 44100
    bpm = 120
    beat_duration = 60.0 / bpm
    num_beats = 8
    total_samples = int(beat_duration * num_beats * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(total_samples):
            t = float(i) / sample_rate
            beat_pos = t % beat_duration
            
            value = 0.0
            # Kick drum on every beat
            if beat_pos < 0.1:
                freq = 150.0 * (1.0 - beat_pos*10)
                value += math.sin(2.0 * math.pi * freq * beat_pos) * 0.8
            
            # Hi-hat on every off-beat
            if 0.5 * beat_duration < beat_pos < 0.5 * beat_duration + 0.05:
                value += random.uniform(-0.5, 0.5) * 0.4
                
            packed_value = struct.pack('h', int(value * 32767.0))
            wav_file.writeframes(packed_value)

generate_beat('music.wav')
print("Music generated!")
