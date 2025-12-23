# 在脚本顶部需要的导入
from m5.ticks import fromSeconds
from m5.util.convert import (
    toLatency,
    toMemoryBandwidth,
)


# 定义序列生成器：该函数接收 PyTrafficGen 实例（命名 pygen）并返回一个迭代器
def returning_sequence(pygen):
    # 此处示例使用 64 字节 block（视你的 cache line 而定）
    block_size = 64

    # 每段我们只想发出一个访问：使用 data_limit = block_size
    data_limit = block_size

    # 速率/周期：给一个较大的带宽以确保段期间可以发送（实际节拍由 period 决定）
    rate = toMemoryBandwidth("1GiB/s")
    period = fromSeconds(
        block_size / rate
    )  # ticks between back-to-back requests

    # 将 human-friendly durations 转为 ticks（与库中 _create_linear_traffic 的做法一致）
    # 这里每段给一个小的 duration（足够运行 data_limit）
    short_duration = fromSeconds(toLatency("1us"))

    # 地址 A, B, C（示例，替换为你希望的具体地址）
    A = 0x0
    B = 0x16384
    C = 0x32768

    # 每个 yield 是一段“子流”；把 min_addr==max_addr 以只访问单个地址
    yield pygen.createLinear(
        short_duration,  # duration (ticks)
        A,  # min_addr
        A,  # max_addr
        block_size,  # block_size
        period,  # min_period
        period,  # max_period
        100,  # rd_perc (100 = reads only)
        data_limit,  # data_limit (bytes) -> 保证只发出一个请求
    )

    yield pygen.createLinear(
        short_duration, B, B, block_size, period, period, 100, data_limit
    )
    yield pygen.createLinear(
        short_duration, A, A, block_size, period, period, 100, data_limit
    )
    yield pygen.createLinear(
        short_duration, C, C, block_size, period, period, 100, data_limit
    )

    # 结束段（可选；否则模拟器会在没有更多段时打印“no phases left”）
    yield pygen.createExit(0)
