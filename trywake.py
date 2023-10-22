from dotenv import load_dotenv
import os
import pvporcupine
import pyaudio
from queue import Empty, Queue


_audio_q = Queue()


def main():
    load_dotenv()    
    PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")

    pv_handle = pvporcupine.create(
        access_key=PICOVOICE_ACCESS_KEY,
        # keyword_paths=["./res/wake-phrases/Yar-Robot-Oh_en_mac_v2_2_0/Yar-Robot-Oh_en_mac_v2_2_0.ppn"],
        keyword_paths=["./res/wake-phrases/Yar-assistant_en_mac_v2_2_0/Yar-assistant_en_mac_v2_2_0.ppn"],
        # keywords=['porcupine']
    )

    print(f"PicoVoice expected sample rate (Hz): {pv_handle.sample_rate}")
    print(f"PicoVoice expected frame length: {pv_handle.frame_length}")

    pa = pyaudio.PyAudio()

    try:
        in_stream = pa.open(
            rate=pv_handle.sample_rate,
            channels=1,
            format=pyaudio.paUInt8,
            input=True,
            frames_per_buffer=pv_handle.frame_length,
            stream_callback=audio_input_stream_callback
        )

        # Infinite loop while we listen. Ctrl+C to exit.
        while True:
            try:
                audio_bytes = _audio_q.get()
            except Empty:
                print("Queue is empty. Skipping.")
                continue

            i_keyword = pv_handle.process(audio_bytes)
            if i_keyword >= 0:
                print(f"Detected keyword with index {i_keyword}")

    except KeyboardInterrupt:
        pass
    finally:
        in_stream.stop_stream()
        in_stream.close()

    pa.terminate()


def audio_input_stream_callback(in_data, frame_count, time_info, status_flags):
    # print(f"frame_count: {frame_count}")
    _audio_q.put(in_data)
    # print(f"qsize: {_audio_q.qsize()}")
    return (None, pyaudio.paContinue)


if __name__ == "__main__":
    main()