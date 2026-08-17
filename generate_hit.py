import wave
import struct
import math
import random

def generate_tone(filename, frequency, duration, volume=0.5, type='sine'):
    sample_rate = 44100.0
    num_samples = int(duration * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Fast exponential decay for percussive sound
            env = math.exp(-t * 20)
            
            if type == 'sine':
                value = math.sin(2.0 * math.pi * frequency * t)
            elif type == 'square':
                value = 1.0 if math.sin(2.0 * math.pi * frequency * t) > 0 else -1.0
            elif type == 'noise':
                value = random.uniform(-1, 1)
            elif type == 'synth_drum':
                # Frequency sweep down + noise for a synth tom/snare
                freq = frequency * math.exp(-t * 15)
                value = math.sin(2.0 * math.pi * freq * t) + 0.2 * random.uniform(-1, 1)
                
            packed_value = struct.pack('h', int(max(-1.0, min(1.0, value * volume * env)) * 32767.0))
            wav_file.writeframes(packed_value)

generate_tone('punch.wav', 600.0, 0.15, volume=0.6, type='synth_drum')
print("New punch.wav generated!")
