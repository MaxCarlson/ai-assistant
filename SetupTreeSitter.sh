git clone https://github.com/tree-sitter/tree-sitter-python.git
git clone https://github.com/tree-sitter/tree-sitter-cpp.git
sudo apt update
sudo apt upgrade build-essential
sudo apt install gcc g++ make cmake
cd tree-sitter-python
mkdir -p build && cd build
cmake .. -DBUILD_SHARED_LIBS=OFF -DTREE_SITTER_ABI_VERSION=14
cmake --build .
cd ../../tree-sitter-cpp
mkdir -p build && cd build
cmake .. -DBUILD_SHARED_LIBS=OFF -DTREE_SITTER_ABI_VERSION=14
cmake --build .
cd ../../
mkdir -p build
gcc -shared -o build/my-languages.so \        
    -Wl,--whole-archive tree-sitter-python/build/libtree-sitter-python.a \
    tree-sitter-cpp/build/libtree-sitter-cpp.a -Wl,--no-whole-archive \
    tree-sitter-python/src/scanner.c \
    -Wl,-u,tree_sitter_python -Wl,-u,tree_sitter_cpp
