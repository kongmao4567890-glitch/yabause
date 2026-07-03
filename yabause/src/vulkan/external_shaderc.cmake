include(FetchContent)
include(ExternalProject)

# Download shaderc source at configure time so headers are available
FetchContent_Declare(
    shaderc_src
    GIT_REPOSITORY https://github.com/google/shaderc.git
    GIT_TAG v2020.5
    GIT_SHALLOW TRUE
)
FetchContent_Populate(shaderc_src)
set(SHADERC_SOURCE_DIR ${shaderc_src_SOURCE_DIR})

# Run git-sync-deps to get glslang, spirv-tools, etc.
execute_process(
    COMMAND python3 utils/git-sync-deps
    WORKING_DIRECTORY ${SHADERC_SOURCE_DIR}
    RESULT_VARIABLE GIT_SYNC_RESULT
)
if(NOT GIT_SYNC_RESULT EQUAL 0)
    message(WARNING "git-sync-deps failed, trying python...")
    execute_process(
        COMMAND python utils/git-sync-deps
        WORKING_DIRECTORY ${SHADERC_SOURCE_DIR}
    )
endif()

set(SHADERC_INCLUDE_DIR ${SHADERC_SOURCE_DIR}/libshaderc/include)

if(ANDROID)
get_filename_component(TOOL_CHAIN_ABSOLUTE_PATH "${CMAKE_TOOLCHAIN_FILE}"
                       REALPATH BASE_DIR "${CMAKE_BINARY_DIR}")

set( ADDITIONAL_CMAKE_ARGS
 -DANDROID_ABI=${ANDROID_ABI}
 -DCMAKE_MAKE_PROGRAM=${CMAKE_MAKE_PROGRAM}
 -DANDROID_NATIVE_API_LEVEL=${ANDROID_NATIVE_API_LEVEL}
 -DCMAKE_TOOLCHAIN_FILE=${TOOL_CHAIN_ABSOLUTE_PATH}
)
else()
  set(ADDITIONAL_CMAKE_ARGS "")
endif()

# Build shaderc as external project (using already-downloaded source)
ExternalProject_Add(
    shaderc
    PREFIX shaderc
    SOURCE_DIR ${SHADERC_SOURCE_DIR}
    DOWNLOAD_COMMAND ""
    UPDATE_COMMAND ""
    CMAKE_ARGS
        -DSHADERC_SKIP_INSTALL=OFF
        -DSHADERC_SKIP_TESTS=ON
        -DSHADERC_SKIP_EXAMPLES=ON
        -DCMAKE_BUILD_TYPE=Release
        -DSHADERC_ENABLE_SHARED_CRT=TRUE
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        ${ADDITIONAL_CMAKE_ARGS}
)

ExternalProject_Get_Property(shaderc BINARY_DIR)
ExternalProject_Get_Property(shaderc INSTALL_DIR)

set(SHADERC_LIBRARY_DIR ${BINARY_DIR}/libshaderc )
if(MSVC)
  set(SHADERC_LIBRARIES ${INSTALL_DIR}/lib/${CMAKE_STATIC_LIBRARY_PREFIX}shaderc_combined${CMAKE_STATIC_LIBRARY_SUFFIX}  )
else()
  set(SHADERC_LIBRARIES ${BINARY_DIR}/libshaderc/${CMAKE_STATIC_LIBRARY_PREFIX}shaderc_combined${CMAKE_STATIC_LIBRARY_SUFFIX} )
endif()
