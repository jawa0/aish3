import ctypes
import queue

from audio_service import AudioService
import pyaudio

# Audio recording parameters
N_SAMPLES_PER_SECOND = 16_000
N_SAMPLE_BYTES = ctypes.sizeof(ctypes.c_int16)  # pyaudio.paInt16
N_CHANNELS = 1
N_CHUNK_SAMPLES = int(N_SAMPLES_PER_SECOND / 5)  # 200ms


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        # self._quit_event = quit_event

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self._audio_stream = None
        self.closed = True


    def __enter__(self):
        """Called on entry to a 'with' block. E.g. 
        with MicrophoeStream(16000, 1600) as stream:
            # do stuff with stream...
        """
        self.start()
        return self


    def __exit__(self, type, value, traceback):
        """Called on exit from a 'with' block. E.g. 
        with MicrophoeStream(16000, 1600) as stream:
            # do stuff with stream...
        """
        self.stop()


    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue


    def get_nowait(self):
        chunks = []
        try:
            while True:
                chunk = self._buff.get_nowait()
                assert(chunk is not None)
                chunks.append(chunk)
        except queue.Empty:
            if not len(chunks):
                return b""

        return b"".join(chunks)


    def start(self):
        self._audio_stream = AudioService.get_voice_input_stream(self._fill_buffer)
        self.closed = False


    def stop(self):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
