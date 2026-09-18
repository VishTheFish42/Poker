add_library(poker_engine
    src/card.cpp
    src/deck.cpp
)

target_include_directories(poker_engine
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(poker_engine PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic>
)

if(POKER_BUILD_TESTS)
    add_subdirectory(tests)
endif()
