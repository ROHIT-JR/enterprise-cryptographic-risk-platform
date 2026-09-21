cmake_minimum_required(VERSION 3.20)
project(core_banking_bridge C)

find_package(OpenSSL REQUIRED)
add_library(core_banking crypto_bridge.c)
target_link_libraries(core_banking OpenSSL::SSL OpenSSL::Crypto)
