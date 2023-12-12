from dotenv import load_dotenv
import os
import platform
import pvporcupine
import pyaudio
from queue import Empty, Queue
import struct


_audio_q = Queue()


def bytes_to_ints(byte_data):
    return struct.unpack(str(len(byte_data) // 2) + 'h', byte_data)


def main():
    load_dotenv()    
    PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")

    keyword_paths = {"macOS": "./res/wake-phrases/Yar-assistant_en_mac_v2_2_0/Yar-assistant_en_mac_v2_2_0.ppn",
           "RaspberryPi": "./res/wake-phrases/Yarr-assistant_en_raspberry_pi_v3_0_0.ppn",
    }

    if platform.system() == "Darwin":
        KEYWORD_PATH = keyword_paths["macOS"]
    elif platform.system() == "Linux" and platform.machine().startswith("armv"):
        KEYWORD_PATH = keyword_paths["RaspberryPi"]
    else:
        raise NotImplementedError("Platform not supported.")
    
    pv_handle = pvporcupine.create(
        access_key=PICOVOICE_ACCESS_KEY,
        keyword_paths=[KEYWORD_PATH],
    )

    print(f"PicoVoice expected sample rate (Hz): {pv_handle.sample_rate}")
    print(f"PicoVoice expected frame length: {pv_handle.frame_length}")

    pa = pyaudio.PyAudio()

    try:
        in_stream = pa.open(
            rate=pv_handle.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=pv_handle.frame_length,
            stream_callback=audio_input_stream_callback
        )

        # Infinite loop while we listen. Ctrl+C to exit.
        while True:
            pass
            try:
                audio_ints = _audio_q.get()
            except Empty:
                print("Queue is empty. Skipping.")
                continue

            i_keyword = pv_handle.process(audio_ints)
            if i_keyword >= 0:
                print(f"Detected keyword with index {i_keyword}")

    except KeyboardInterrupt:
        pass
    finally:
        in_stream.stop_stream()
        in_stream.close()

    pv_handle.delete()
    pa.terminate()


def audio_input_stream_callback(in_data, frame_count, time_info, status_flags):
    # print('audio_input_stream_callback')
    # print(f" frame_count: {frame_count}")
    # print(f" in_data length: {len(in_data)}")
    
    # print type of in_data
    # print(type(in_data))

    ints = bytes_to_ints(in_data)
    _audio_q.put(ints)
    # print(f"qsize: {_audio_q.qsize()}")
    return (None, pyaudio.paContinue)


if __name__ == "__main__":
    main()