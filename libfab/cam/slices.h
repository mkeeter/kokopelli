#ifndef SLICES_H
#define SLICES_H

#include <stdint.h>

/*  find_support
 *
 *  Determines whether or not a pixel is supported.
 *  'curr' should be a binary input image with pixels set to
 *  either 0 or 255.  After running, the pixels will be set to
 *  SUPPORTED, NEEDS_SUPPORT, or CANNOT_SUPPORT.
 */
void find_support(const int ni, const int nj,
                  uint8_t const*const*const prev,
                  uint8_t* const*const curr);

/*  next_slice
 *
 *  Modifies 'curr' so that it can be used as 'prev' in find_support
 *  'curr' should be an lattice where solid is represented by
 *  non-zero pixels.  After running, its pixels will be set to
 *  FILLED, BLOCKED, and UNBLOCKED as appropriate.
 *
 *  support_offset is the maximum horizontal offset at which a lower
 *  layer can support an upper layer (measured in mm)
 */
void next_slice(const int ni, const int nj,
                const float pixels_per_mm,
                const float support_offset,
                uint8_t const*const*const prev,
                uint8_t* const*const curr);
#endif
