# Prefer an already-installed GoogleTest (e.g. `brew install googletest`) and
# only fall back to fetching source so a machine without network access but
# with the package installed still builds.
find_package(GTest CONFIG QUIET)
if(NOT GTest_FOUND)
    include(FetchContent)
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.18.0
    )
    # Match the parent project's runtime library settings on Windows/MSVC.
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
endif()

add_executable(poker_engine_tests
    test_card.cpp
    test_deck.cpp
    test_hand_evaluator.cpp
    test_player.cpp
    test_table.cpp
    test_betting_round.cpp
    test_pot_manager.cpp
    test_showdown.cpp
)

target_link_libraries(poker_engine_tests
    PRIVATE poker_engine GTest::gtest GTest::gtest_main
)

include(GoogleTest)
gtest_discover_tests(poker_engine_tests)
