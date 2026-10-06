// REFERENCE: type this into include/Camera.h yourself.
//
// Camera class from Fire Emblem: Three Houses v1.2.0.
// Field names are ours (the originals were stripped); offsets are verified
// against the game's code. Matches the struct you built in Ghidra.
#pragma once

#include <arm_neon.h>

typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;

// 16-byte vector: position (x, y, z) plus a w the engine uses for matrix math.
// The game copies it as two 8-byte halves. Assignment copies zw first, then xy:
// that byte-matches Camera::Set. (SetDeferred copies xy first, so it spells its
// copies out member by member instead of using operator=.)
struct Vec4 {
    union {
        struct { float x, y, z, w; };
        struct { float32x2_t xy, zw; };
    };
    Vec4 &operator=(const Vec4 &o) {
        zw = o.zw;
        xy = o.xy;
        return *this;
    }
};

// 4x4 matrix stored as four NEON rows. Row-vector convention: v * M.
struct Mtx44 {
    float32x4_t r[4];
};

class Camera {
public:
    Camera *Set(const Vec4 *eye, const Vec4 *target, const Vec4 *up, float unk150,
                float fovY, float nearZ, float farZ, float aspect, float unk15C);   // 0x7100A32DB0
    void SetDeferred(const Vec4 *eye, const Vec4 *target, const Vec4 *up, float unk150,
                     float fovY, float nearZ, float farZ, float aspect);           // 0x7100A32EA0
    void UpdateView();                                                              // 0x7100A328B0
    void UpdateProjection();                                                        // 0x7100A32B50

    u8    _pad00[0x10];   // 0x00  unknown (vtable? flags?)
    Vec4  mEye;           // 0x10  camera position
    Vec4  mTarget;        // 0x20  point the camera looks at
    Vec4  mUp;            // 0x30  up direction
    Mtx44 mWorld;         // 0x40  camera orientation (built by UpdateView)
    Mtx44 mView;          // 0x80  world -> camera
    Mtx44 mProj;          // 0xC0  camera -> screen   (mProj_00 = 0xC0, mProj_11 = 0xD4, ...)
    Mtx44 mViewProj;      // 0x100 mView * mProj
    float mNear;          // 0x140 near clip plane
    float mFar;           // 0x144 far clip plane
    float mFovY;          // 0x148 vertical field of view, radians
    float mAspect;        // 0x14C width / height  (16/9 in vanilla)
    float mUnk150;        // 0x150 callers pass 0.0
    float mUnk154;        // 0x154 Set() forces 1.0
    u32   mFlags;         // 0x158 bit0: ortho from distance, bit1: swap near/far (reverse-Z)
    float mUnk15C;        // 0x15C callers pass 1.0
    u8    mViewDirty;     // 0x160
    u8    mProjDirty;     // 0x161
};

static_assert(__builtin_offsetof(Camera, mEye) == 0x10, "layout");
static_assert(__builtin_offsetof(Camera, mWorld) == 0x40, "layout");
static_assert(__builtin_offsetof(Camera, mViewProj) == 0x100, "layout");
static_assert(__builtin_offsetof(Camera, mFovY) == 0x148, "layout");
static_assert(__builtin_offsetof(Camera, mProjDirty) == 0x161, "layout");
