# pybind11 module exposing the engine to Python as `poker_engine`, for the
# AI layer (src/poker/ai/) - see specs/design.md. Enabled with
# -DPOKER_BUILD_PYTHON_BINDINGS=ON; the module lands in build/bindings/.

# Build against the project's virtualenv interpreter by default, so the
# module's ABI matches the Python that runs the AI layer and its tests.
# Pass -DPython_EXECUTABLE=... to use a different one.
if(NOT DEFINED Python_EXECUTABLE)
    if(EXISTS "${PROJECT_SOURCE_DIR}/.venv/bin/python")
        set(Python_EXECUTABLE "${PROJECT_SOURCE_DIR}/.venv/bin/python")
    elseif(EXISTS "${PROJECT_SOURCE_DIR}/.venv/Scripts/python.exe")
        set(Python_EXECUTABLE "${PROJECT_SOURCE_DIR}/.venv/Scripts/python.exe")
    endif()
endif()
set(PYBIND11_FINDPYTHON ON)

# Same pattern as GoogleTest: prefer an installed pybind11, fetch otherwise.
find_package(pybind11 CONFIG QUIET)
if(NOT pybind11_FOUND)
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.13.6
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# The static engine library gets linked into a shared module.
set_target_properties(poker_engine PROPERTIES POSITION_INDEPENDENT_CODE ON)

pybind11_add_module(poker_engine_py module.cpp)
set_target_properties(poker_engine_py PROPERTIES OUTPUT_NAME poker_engine)
target_link_libraries(poker_engine_py PRIVATE poker_engine)
