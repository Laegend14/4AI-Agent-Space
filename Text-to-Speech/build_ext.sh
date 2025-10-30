chmod +x ./bazelisk-linux-amd64
USE_BAZEL_VERSION=5.0.0 ./bazelisk-linux-amd64 build wavegru_mod -c opt --copt=-march=native
cp -f bazel-bin/wavegru_mod.so .
