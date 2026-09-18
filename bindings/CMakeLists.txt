# pybind11 module exposing `poker_engine` to the Python AI layer
# (src/poker/ai/), per specs/design.md's "C++ engine + Python AI" split.
#
# Not implemented yet - the engine itself (card/deck/hand evaluator/player/
# table/betting/pot/showdown/controller) needs to exist first. See
# specs/tasks.md Phase 8. Enable with -DPOKER_BUILD_PYTHON_BINDINGS=ON once
# there's a module to build here.

include(FetchContent)
FetchContent_Declare(
    pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG v2.13.6
)
FetchContent_MakeAvailable(pybind11)

# pybind11_add_module(poker_engine_py module.cpp)
# target_link_libraries(poker_engine_py PRIVATE poker_engine)
