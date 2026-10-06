#include "camera.h"

// mViewProj = a * b, one output row at a time.
static inline Mtx44 operator *(const Mtx44 &a, const Mtx44 &b) {
  float32x4_t a0 = a.r[0], a1 = a.r[1], a2 = a.r[2], a3 = a.r[3];
  float32x4_t b0 = b.r[0], b1 = b.r[1], b2 = b.r[2], b3 = b.r[3];
  Mtx44 o;
  o.r[0] = vfmaq_laneq_f32(vfmaq_laneq_f32(vfmaq_laneq_f32(vmulq_laneq_f32(b0, a0, 0), b1, a0, 1), b2, a0, 2), b3, a0, 3);
  o.r[1] = vfmaq_laneq_f32(vfmaq_laneq_f32(vfmaq_laneq_f32(vmulq_laneq_f32(b0, a1, 0), b1, a1, 1), b2, a1, 2), b3, a1, 3);
  o.r[2] = vfmaq_laneq_f32(vfmaq_laneq_f32(vfmaq_laneq_f32(vmulq_laneq_f32(b0, a2, 0), b1, a2, 1), b2, a2, 2), b3, a2, 3);
  o.r[3] = vfmaq_laneq_f32(vfmaq_laneq_f32(vfmaq_laneq_f32(vmulq_laneq_f32(b0, a3, 0), b1, a3, 1), b2, a3, 2), b3, a3, 3);
  return o;
}

// 0x7100A32DB0 status: matching (clang 5.0.1 / 6.0.x, -O2 -g)

Camera *Camera::Set(const Vec4 *eye, const Vec4 *target, const Vec4 *up, float unk150,
                    float fovY, float nearZ, float farZ, float aspect, float unk15C) {
    mUnk154 = 1.0f;
    mEye = *eye;
    mTarget = *target;
    mUp = *up;
    mUnk150 = unk150;
    mFovY = fovY;  
    mNear = nearZ;
    mFar = farZ;
    mAspect = aspect; 
    mUnk15C = unk15C;
    mViewDirty = 0;
    mProjDirty = 1;
    UpdateView();
    if (mProjDirty) {
        mProjDirty = 0;
        UpdateProjection();
    }
    mViewProj = mView * mProj;
    return this;
}

// 0x7100A32EA0 status: nonmatching (95%, mAspect store one slot late; see docs/notes/camera.md)
void Camera::SetDeferred(const Vec4 *eye, const Vec4 *target, const Vec4 *up, float unk150,
                         float fovY, float nearZ, float farZ, float aspect) {
  mEye.xy = eye->xy;
  mEye.zw = eye->zw;
  mTarget.xy = target->xy;
  mTarget.zw = target->zw;
  mUp.xy = up->xy;
  mUp.zw = up->zw;
  mUnk150 = unk150;
  mFovY = fovY;
  mNear = nearZ;
  mFar = farZ;
  mAspect = aspect;
  mViewDirty = 1;
  mProjDirty = 1;
}
