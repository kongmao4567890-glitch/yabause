/* Dot-clear presentation pipeline. Integration: GPL-2.0-or-later.
 * Shader algorithms have separate terms in phosphor-dot-v3.3/NOTICE.md.
 * Included after YglCompileDisplayShader in yglshaderes.c.
 */
#include "DotClearShaders.h"

static GLuint dot_programs[3], dot_textures[2], dot_fbos[2], dot_vao;
static GLuint dot_sampler;
static int dot_sizes[2][2], dot_failed;
static GLint dot_uniforms[3][6];

static void YglResetDotClear(void) {
  int i;
  for (i = 0; i < 3; ++i) dot_programs[i] = 0;
  for (i = 0; i < 2; ++i) {
    dot_textures[i] = dot_fbos[i] = 0;
    dot_sizes[i][0] = dot_sizes[i][1] = 0;
  }
  dot_vao = dot_sampler = 0;
  dot_failed = 0;
}

static void YglDeleteDotClear(void) {
  int i;
  for (i = 0; i < 3; ++i)
    if (dot_programs[i]) glDeleteProgram(dot_programs[i]);
  glDeleteTextures(2, dot_textures);
  glDeleteFramebuffers(2, dot_fbos);
  if (dot_vao) glDeleteVertexArrays(1, &dot_vao);
  if (dot_sampler) glDeleteSamplers(1, &dot_sampler);
  YglResetDotClear();
}

static int YglInitDotClear(void) {
  static const char *const names[] = {
    "Texture", "InputSize", "TextureSize", "OrigInputSize", "OutputSize", "uRotate"
  };
  int i, j;
  if (dot_failed) return -1;
  if (dot_programs[2]) return 0;
  for (i = 0; i < 3; ++i) {
    GLint linked = GL_FALSE;
    GLuint v = YglCompileDisplayShader(GL_VERTEX_SHADER, AA_DOT_CLEAR, display_filter_vertex);
    GLuint f = YglCompileDisplayShader(GL_FRAGMENT_SHADER, AA_DOT_CLEAR, dot_clear_fragments[i]);
    if (v && f) {
      dot_programs[i] = glCreateProgram();
      glAttachShader(dot_programs[i], v);
      glAttachShader(dot_programs[i], f);
      glLinkProgram(dot_programs[i]);
      glGetProgramiv(dot_programs[i], GL_LINK_STATUS, &linked);
    }
    if (v) glDeleteShader(v);
    if (f) glDeleteShader(f);
    if (!linked) {
      YGLLOG("Dot-clear: pass %d failed to link\n", i);
      YglDeleteDotClear();
      dot_failed = 1;
      return -1;
    }
    for (j = 0; j < 6; ++j) dot_uniforms[i][j] = glGetUniformLocation(dot_programs[i], names[j]);
  }
  glGenVertexArrays(1, &dot_vao);
  glGenTextures(2, dot_textures);
  glGenFramebuffers(2, dot_fbos);
  glGenSamplers(1, &dot_sampler);
  glSamplerParameteri(dot_sampler, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
  glSamplerParameteri(dot_sampler, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
  glSamplerParameteri(dot_sampler, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
  glSamplerParameteri(dot_sampler, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
  return 0;
}

static int YglBlitDotClear(u32 source, int width, int height) {
  GLint oldProgram, oldVao, oldActive, oldTexture, oldSampler, oldFbo, oldViewport[4];
  GLboolean depth, blend, stencil, scissor;
#if !defined(_OGLES3_)
  GLboolean srgb = glIsEnabled(GL_FRAMEBUFFER_SRGB);
#endif
  int i, rotate, srcWidth, srcHeight, nativeWidth, nativeHeight, result = -1;
  if (!_Ygl || width <= 0 || height <= 0 || YglInitDotClear() != 0) return -1;
  rotate = _Ygl->rotate_screen && _Ygl->resolution_mode != RES_NATIVE;
  srcWidth = rotate ? _Ygl->height : _Ygl->width;
  srcHeight = rotate ? _Ygl->width : _Ygl->height;
  nativeWidth = _Ygl->rwidth > 0 ? _Ygl->rwidth : 320;
  nativeHeight = _Ygl->rheight > 0 ? _Ygl->rheight : 224;
  if (_Ygl->rotate_screen) { int tmp = nativeWidth; nativeWidth = nativeHeight; nativeHeight = tmp; }
  if (srcWidth <= 0 || srcHeight <= 0) return -1;

  glGetIntegerv(GL_CURRENT_PROGRAM, &oldProgram);
  glGetIntegerv(GL_VERTEX_ARRAY_BINDING, &oldVao);
  glGetIntegerv(GL_ACTIVE_TEXTURE, &oldActive);
  glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &oldFbo);
  glGetIntegerv(GL_VIEWPORT, oldViewport);
  glActiveTexture(GL_TEXTURE0);
  glGetIntegerv(GL_TEXTURE_BINDING_2D, &oldTexture);
  glGetIntegerv(GL_SAMPLER_BINDING, &oldSampler);
  depth = glIsEnabled(GL_DEPTH_TEST); blend = glIsEnabled(GL_BLEND);
  stencil = glIsEnabled(GL_STENCIL_TEST); scissor = glIsEnabled(GL_SCISSOR_TEST);
  glDisable(GL_DEPTH_TEST); glDisable(GL_BLEND);
  glDisable(GL_STENCIL_TEST); glDisable(GL_SCISSOR_TEST);
  glBindVertexArray(dot_vao);
  glBindSampler(0, dot_sampler);

  for (i = 0; i < 2; ++i) {
    int w = i == 0 ? srcWidth : width, h = i == 0 ? srcHeight : height;
    glBindTexture(GL_TEXTURE_2D, dot_textures[i]);
    if (dot_sizes[i][0] != w || dot_sizes[i][1] != h) {
      glTexImage2D(GL_TEXTURE_2D, 0, i == 0 ? GL_SRGB8_ALPHA8 : GL_RGBA8,
          w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
      dot_sizes[i][0] = w; dot_sizes[i][1] = h;
    }
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, dot_fbos[i]);
    glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, dot_textures[i], 0);
    if (glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) goto restore;
  }
  for (i = 0; i < 3; ++i) {
    int inW = i == 2 ? width : srcWidth, inH = i == 2 ? height : srcHeight;
    int outW = i == 0 ? srcWidth : width, outH = i == 0 ? srcHeight : height;
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, i < 2 ? dot_fbos[i] : (GLuint)oldFbo);
    if (i < 2) glViewport(0, 0, outW, outH);
    else {
      glViewport(oldViewport[0], oldViewport[1], oldViewport[2], oldViewport[3]);
      if (scissor) glEnable(GL_SCISSOR_TEST);
    }
#if !defined(_OGLES3_)
    if (i == 0) glEnable(GL_FRAMEBUFFER_SRGB); else glDisable(GL_FRAMEBUFFER_SRGB);
#endif
    glUseProgram(dot_programs[i]);
    glBindTexture(GL_TEXTURE_2D, i == 0 ? source : dot_textures[i - 1]);
    glUniform1i(dot_uniforms[i][0], 0);
    glUniform2f(dot_uniforms[i][1], (float)inW, (float)inH);
    glUniform2f(dot_uniforms[i][2], (float)inW, (float)inH);
    glUniform2f(dot_uniforms[i][3], (float)nativeWidth, (float)nativeHeight);
    glUniform2f(dot_uniforms[i][4], (float)outW, (float)outH);
    glUniform1i(dot_uniforms[i][5], i == 0 ? rotate : 0);
    glDrawArrays(GL_TRIANGLES, 0, 3);
  }
  result = 0;
restore:
  glBindFramebuffer(GL_DRAW_FRAMEBUFFER, oldFbo);
  glViewport(oldViewport[0], oldViewport[1], oldViewport[2], oldViewport[3]);
  glBindTexture(GL_TEXTURE_2D, oldTexture);
  glBindSampler(0, oldSampler);
  glActiveTexture(oldActive);
  glBindVertexArray(oldVao); glUseProgram(oldProgram);
  if (depth) glEnable(GL_DEPTH_TEST);
  if (blend) glEnable(GL_BLEND);
  if (stencil) glEnable(GL_STENCIL_TEST);
  if (scissor) glEnable(GL_SCISSOR_TEST);
#if !defined(_OGLES3_)
  if (srgb) glEnable(GL_FRAMEBUFFER_SRGB); else glDisable(GL_FRAMEBUFFER_SRGB);
#endif
  return result;
}
