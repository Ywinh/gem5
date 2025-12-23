#include <stdint.h>

#include <cstdio>
#include <cstdlib>

// 配置区域：根据你的仿真环境调整
// 假设 Cache Line 大小为 64 Bytes
#define CACHE_LINE_SIZE 64
// 定义一个数组大小，比如 32KB (8192个int)
// 如果你的 L1 Cache 是 16KB，这个数组的一半就能把它填满
#define ARRAY_SIZE (32 * 1024 / sizeof(int))

// 使用 volatile 防止编译器把读操作优化掉
// 强制 CPU 每次必须真的去访问内存地址
void test_sequential(volatile int* arr, int size) {
    printf("[Phase 1] Sequential Access (Testing Spatial Locality)...\n");
    // 预期：
    // 第1次访问 arr[0] -> Miss (冷启动) -> 搬运整个 Cache Line (包含 arr[0]...arr[15])
    // 第2-16次访问 arr[1]...arr[15] -> Hit (空间局部性)
    // 第17次访问 arr[16] -> Miss -> 搬运下一个 Line
    volatile int sum = 0;
    for (int i = 0; i < size; i++) {
        sum += arr[i];
    }
}

void test_temporal(volatile int* arr, int size) {
    printf("[Phase 2] Looping Access (Testing Temporal Locality)...\n");
    // 预期：
    // 如果 size 小于 Cache 容量，第一次循环后数据都在 Cache 里
    // 第二次循环应该全是 Hit
    volatile int sum = 0;
    // 只访问前 4KB 数据，确保能塞进 L1 Cache
    int small_size = (4 * 1024 / sizeof(int));

    for (int loop = 0; loop < 5; loop++) {
        for (int i = 0; i < small_size; i++) {
            sum += arr[i];
        }
    }
}

void test_stride(volatile int* arr, int size) {
    printf("[Phase 3] Strided Access (Testing Cache Lines & Prefetcher)...\n");
    // 步长设为 Cache Line 的大小 (64B / 4B = 16 ints)
    // 预期：
    // 每次访问都会跳到下一个 Cache Line 的开头
    // 这会产生 100% 的 Miss (除非有硬件预取器检测到步长)
    int stride = CACHE_LINE_SIZE / sizeof(int);
    volatile int sum = 0;

    for (int i = 0; i < size; i += stride) {
        sum += arr[i];
    }
}

int main() {
    // 在堆上分配内存，模拟真实的数据处理
    volatile int* buffer = (volatile int*)malloc(ARRAY_SIZE * sizeof(int));
    if (buffer == NULL) {
        printf("Memory allocation failed!\n");
        return -1;
    }

    // 初始化数据 (Write Miss + Dirty)
    for (int i = 0; i < ARRAY_SIZE; i++) {
        buffer[i] = i;
    }

    printf("=== Cache Test Started ===\n");
    printf("Array Size: %lu KB\n", (ARRAY_SIZE * sizeof(int))/1024);

    test_sequential(buffer, ARRAY_SIZE);
    test_temporal(buffer, ARRAY_SIZE);
    test_stride(buffer, ARRAY_SIZE);

    printf("=== Cache Test Finished ===\n");

    free((void*)buffer);
    return 0;
}
