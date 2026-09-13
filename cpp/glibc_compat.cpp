#if defined(__linux__)
#include <features.h>

#if defined(__GLIBC__) && !__GLIBC_PREREQ(2, 38)
#include <cstdarg>
#include <cstdio>

// Filament 1.76.1's Linux SDK is built on glibc 2.38+ and references the C23
// scanf entry point. The formats used by Filament are supported by the older
// ISO C99 implementation, so provide the ABI entry point on manylinux_2_34.
extern "C" int __isoc23_sscanf(const char* input, const char* format, ...) {
    va_list arguments;
    va_start(arguments, format);
    const int result = std::vsscanf(input, format, arguments);
    va_end(arguments);
    return result;
}
#endif
#endif
