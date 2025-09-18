from shared_mem.buffers import DoubleRingBuffer

def test_buffer_append():
    buf = DoubleRingBuffer(short_len=3, long_len=5)
    for i in range(10):
        buf.append({"price": i})
    assert len(buf.get_short()) == 3
    assert len(buf.get_long()) == 5