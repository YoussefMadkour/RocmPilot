"""Curated ROCm/HIP migration knowledge — the seed corpus for the RAG index.

OWNER: Youssef (AI). Hand-curated, authoritative facts about porting CUDA-first
PyTorch repos to AMD ROCm. Kept as data (not scraped) so the KB is deterministic
and reviewable; expand it over time. `ingest_docs.py` embeds these and upserts
them into Qdrant.

Each entry: {"text": <self-contained fact>, "source": <where it comes from>}.
"""
from __future__ import annotations

SEED_DOCS: list[dict[str, str]] = [
    {
        "text": "On AMD ROCm, PyTorch exposes GPUs through the SAME torch.cuda "
                "namespace as NVIDIA. torch.cuda.is_available() returns True, "
                "'cuda' device strings and .cuda()/.to('cuda') work unchanged — "
                "they run on HIP under the hood. Do NOT rename 'cuda' to 'rocm'; "
                "the goal is removing NVIDIA-only assumptions, not renaming devices.",
        "source": "ROCm PyTorch porting guide",
    },
    {
        "text": "Select specific AMD GPUs with HIP_VISIBLE_DEVICES, not "
                "CUDA_VISIBLE_DEVICES. CUDA_VISIBLE_DEVICES is ignored by the ROCm "
                "runtime. Example: HIP_VISIBLE_DEVICES=0,1 python train.py.",
        "source": "ROCm environment variables",
    },
    {
        "text": "Install a ROCm PyTorch build instead of CUDA wheels. Replace a "
                "'+cu121'-style CUDA wheel with the ROCm index, e.g. "
                "pip install torch --index-url https://download.pytorch.org/whl/rocm6.2 . "
                "Installing torch from a requirements.txt that pins +cuXXX will "
                "clobber the ROCm build inside a rocm/pytorch container.",
        "source": "PyTorch ROCm install",
    },
    {
        "text": "Use an official ROCm base image (e.g. rocm/pytorch) instead of "
                "nvidia/cuda in your Dockerfile. The rocm/pytorch image already "
                "ships a HIP-enabled torch build.",
        "source": "ROCm Docker guide",
    },
    {
        "text": "Run a ROCm container with the AMD compute devices exposed: "
                "docker run --device=/dev/kfd --device=/dev/dri --group-add video "
                "--security-opt seccomp=unconfined <image>. The NVIDIA flags "
                "--gpus all and the nvidia-container-runtime are not used on ROCm.",
        "source": "ROCm Docker guide",
    },
    {
        "text": "HIPIFY converts CUDA source to portable HIP. hipify-perl is a fast "
                "sed-like translator; hipify-clang is AST-based and more accurate. "
                "Run hipify-perl mykernel.cu > mykernel.hip, then build for ROCm. "
                "Custom .cu/.cuh kernels cannot be auto-ported by device-string "
                "rewrites — they must be HIPified and rebuilt.",
        "source": "AMD HIPIFY documentation",
    },
    {
        "text": "PyTorch custom C++/CUDA extensions (torch.utils.cpp_extension, "
                "CUDAExtension, load_inline) support ROCm/HIP: on a ROCm torch "
                "build the sources are hipified at build time. Kernels using raw "
                "CUDA intrinsics still need manual HIP porting.",
        "source": "PyTorch cpp_extension on ROCm",
    },
    {
        "text": "Replace nvidia-smi with rocm-smi (utilization, memory, clocks) and "
                "rocminfo (device/agent details, gfx architecture) on AMD hosts.",
        "source": "ROCm tooling",
    },
    {
        "text": "NVIDIA Apex is not for ROCm, and most of it is unnecessary: mixed "
                "precision is native via torch.cuda.amp (torch.autocast), and fused "
                "optimizers / distributed training are in torch. Remove apex and use "
                "the upstream torch equivalents.",
        "source": "ROCm migration: dependencies",
    },
    {
        "text": "bitsandbytes was historically CUDA-only; recent versions add a "
                "multi-backend build with experimental ROCm support. Verify the ROCm "
                "backend for your GPU arch, or drop 8-bit quantization if unsupported.",
        "source": "ROCm migration: dependencies",
    },
    {
        "text": "Upstream flash-attn is CUDA-only. On AMD, use the ROCm flash-attention "
                "port (built on Composable Kernel) or torch's built-in "
                "scaled_dot_product_attention, which has a ROCm-supported backend.",
        "source": "ROCm migration: attention",
    },
    {
        "text": "torch.backends.cudnn settings map to MIOpen on ROCm and are generally "
                "safe to leave as-is; cudnn.benchmark still tunes kernels. There is no "
                "separate 'rocm' backends namespace to switch to.",
        "source": "ROCm PyTorch backends",
    },
    {
        "text": "TF32 flags (torch.backends.cuda.matmul.allow_tf32) are NVIDIA Ampere "
                "concepts; on AMD they are effectively no-ops. MI200/MI300 GPUs get "
                "reduced-precision matmul acceleration through hipBLASLt automatically.",
        "source": "ROCm PyTorch backends",
    },
    {
        "text": "HIP error 'no HIP devices are available' / hipErrorNoDevice usually "
                "means the container can't see the GPU: mount --device=/dev/kfd and "
                "--device=/dev/dri, add the user to the video/render group, and confirm "
                "the host has the amdgpu/ROCm driver (check with rocminfo).",
        "source": "ROCm troubleshooting",
    },
    {
        "text": "HIP error 'the operation cannot be performed in the present state' "
                "often indicates an unsupported GPU architecture or a torch/ROCm "
                "version mismatch. Set PYTORCH_ROCM_ARCH to your gfx target (e.g. "
                "gfx942 for MI300) and match the torch ROCm build to the installed "
                "ROCm runtime.",
        "source": "ROCm troubleshooting",
    },
    {
        "text": "cupy has a ROCm build: install cupy-rocm (matching your ROCm version) "
                "instead of cupy-cuda11x/cupy-cuda12x. Some CUDA-specific cupy APIs may "
                "be unavailable on ROCm.",
        "source": "ROCm migration: dependencies",
    },
    {
        "text": "A pragmatic AMD readiness order: (1) swap the base image and wheels "
                "off NVIDIA/CUDA, (2) keep 'cuda' device code as-is (ROCm handles it), "
                "(3) HIPIFY any custom .cu kernels, (4) validate with a smoke test that "
                "runs a real matmul on the device and prints PASS/FAIL.",
        "source": "RocmPilot playbook",
    },

    # ---- Warp / wavefront (the hard 20%) ----
    {
        "text": "The single biggest kernel-porting hazard: NVIDIA warps are 32 threads, "
                "AMD wavefronts are 64 (on CDNA / MI2xx/MI3xx). Any kernel that hardcodes "
                "32, masks with 0xffffffff, or assumes a 32-lane reduction must be "
                "re-derived for 64-wide wavefronts. hipify translates syntax but does NOT "
                "fix this logic — it is manual.",
        "source": "ROCm kernel porting: wavefront64",
    },
    {
        "text": "__shfl_sync / __shfl_down_sync / __shfl_up_sync / __shfl_xor_sync exist "
                "in HIP, but shuffle-based warp reductions written for 32 lanes give wrong "
                "results on 64-lane wavefronts. Rewrite the reduction tree for 64 lanes, "
                "or use rocPRIM/hipCUB block primitives instead of hand-rolled shuffles.",
        "source": "ROCm kernel porting: warp shuffle",
    },
    {
        "text": "Warp vote/ballot intrinsics (__ballot_sync, __any_sync, __all_sync, "
                "__activemask) return a lane mask. On NVIDIA it is 32-bit; on AMD the "
                "wavefront mask is 64-bit (unsigned long long). Code that stores a ballot "
                "result in a 32-bit int or shifts by <32 will silently drop lanes 32-63.",
        "source": "ROCm kernel porting: ballot/vote",
    },
    {
        "text": "__syncwarp() has HIP support but warp-synchronous programming that relies "
                "on 32-lane lockstep is fragile on 64-wide wavefronts. Prefer explicit "
                "__syncthreads() at the block level or block-wide primitives.",
        "source": "ROCm kernel porting: sync",
    },

    # ---- HIPIFY specifics ----
    {
        "text": "hipify-perl is a fast regex/sed translator (good for a first pass, may "
                "miss edge cases); hipify-clang is AST-based and more accurate but needs a "
                "working CUDA install to parse. Typical flow: hipify-perl kernel.cu > "
                "kernel.hip, then fix residual warnings hipify emits as HIP_TODO comments.",
        "source": "AMD HIPIFY: perl vs clang",
    },
    {
        "text": "After hipify, compile with hipcc. Common residuals hipify cannot resolve: "
                "warp-size assumptions, inline PTX asm (must be rewritten as HIP/GCN or "
                "removed), __launch_bounds__ tuning, and library handles (cuBLAS handle -> "
                "hipBLAS handle). These are the manual tail.",
        "source": "AMD HIPIFY: residuals",
    },
    {
        "text": "Inline PTX assembly (asm volatile with PTX) has NO automatic translation "
                "to AMD GCN/RDNA ISA. hipify leaves it untouched and it will not compile. "
                "Rewrite the intent in HIP C++ or with AMD GCN intrinsics — always manual.",
        "source": "ROCm kernel porting: inline asm",
    },

    # ---- Library one-liners (retrieval-friendly) ----
    {"text": "cuBLAS maps to hipBLAS (portability layer) or rocBLAS (native). For GEMM "
             "autotuning use hipBLASLt. API is largely 1:1: cublasHandle_t -> hipblasHandle_t.",
     "source": "ROCm libraries: BLAS"},
    {"text": "cuDNN maps to MIOpen on ROCm. Not header-compatible; port cudnn* calls to "
             "miopen* equivalents. PyTorch/TensorFlow ROCm builds already use MIOpen "
             "internally, so high-level framework code needs no change.",
     "source": "ROCm libraries: MIOpen"},
    {"text": "NCCL maps to RCCL on ROCm, which is API-compatible (ncclAllReduce -> same "
             "signature). Often just a link/library swap. Multi-GPU collectives work on "
             "Infinity Fabric.",
     "source": "ROCm libraries: RCCL"},
    {"text": "cuFFT -> hipFFT/rocFFT; cuSPARSE -> hipSPARSE/rocSPARSE; cuRAND -> "
             "hipRAND/rocRAND; cuSOLVER -> hipSOLVER/rocSOLVER; Thrust -> rocThrust "
             "(near drop-in). CUB -> hipCUB / rocPRIM.",
     "source": "ROCm libraries: map table"},
    {"text": "CUTLASS has no drop-in ROCm port. For high-performance GEMM/conv on AMD "
             "use Composable Kernel (CK) or hipBLASLt. This is a significant rewrite, not "
             "a translation — budget engineering time.",
     "source": "ROCm libraries: CUTLASS"},

    # ---- Validation / deployment ----
    {"text": "To run a ROCm container: docker run --device=/dev/kfd --device=/dev/dri "
             "--group-add video --security-opt seccomp=unconfined <image>. Verify inside "
             "with rocminfo (lists gfx arch) and python -c 'import torch; "
             "print(torch.cuda.is_available(), torch.version.hip)'.",
     "source": "ROCm deployment: container run"},
    {"text": "PYTORCH_ROCM_ARCH pins the GPU target for source builds and some kernels: "
             "gfx90a (MI200), gfx942 (MI300). A mismatch between the built arch and the "
             "runtime GPU causes 'invalid device function' or 'operation cannot be "
             "performed in the present state' errors.",
     "source": "ROCm troubleshooting: arch"},
]
