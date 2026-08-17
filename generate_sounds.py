import wave
import struct
import math

def generate_tone(filename, frequency, duration, volume=0.5, type='sine'):
    sample_rate = 44100.0
    num_samples = int(duration * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            if type == 'sine':
                value = math.sin(2.0 * math.pi * frequency * t)
            elif type == 'square':
                value = 1.0 if math.sin(2.0 * math.pi * frequency * t) > 0 else -1.0
            
            # Envelope (fade in / out to avoid clicks)
            env = 1.0
            if i < 1000: env = i / 1000.0
            elif i > num_samples - 1000: env = (num_samples - i) / 1000.0
                
            packed_value = struct.pack('h', int(value * volume * env * 32767.0))
            wav_file.writeframes(packed_value)

# Success chime: two fast high notes
generate_tone('success.wav', 880.0, 0.1, type='sine')
# Note: we'll just use a simple beep for success for now

# Error beep: lower note
generate_tone('fail.wav', 220.0, 0.3, type='square')

print("Sounds generated!")
