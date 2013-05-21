#include <stdlib.h>
#include <stdint.h>

// Slices for 3d printing and other fun stuff

#include "cam/slices.h"
#include "cam/distance.h"

// These values are assigned to the current slice
#define SUPPORTED       255
#define NEEDS_SUPPORT   200
#define CANNOT_SUPPORT  100

// These values are defined for the previous slice
#define FILLED          255
#define BLOCKED         100
#define UNBLOCKED       0

void find_support(const int ni, const int nj,
                  uint8_t const*const*const prev,
                  uint8_t* const*const curr)
{
    for (int j=0; j < nj; ++j) {
        for (int i=0; i < ni; ++i) {
            if (!curr[j][i])
                continue;
            else if (prev[j][i] == FILLED)
                curr[j][i] = SUPPORTED;
            else if (prev[j][i] == UNBLOCKED)
                curr[j][i] = NEEDS_SUPPORT;
            else if (prev[j][i] == BLOCKED)
                curr[j][i] = CANNOT_SUPPORT;
        }
    }
}


void colorize_slice(const int ni, const int nj,
                    uint8_t const*const*const curr,
                    uint8_t (**out)[3])
{
    for (int j=0; j < nj; ++j) {
        for (int i=0; i < ni; ++i) {
            if (curr[j][i] == SUPPORTED) {
                out[j][i][0] = 255;
                out[j][i][1] = 255;
                out[j][i][2] = 255;
            } else if (curr[j][i] == NEEDS_SUPPORT) {
                out[j][i][1] = 255;
            } else if (curr[j][i] == CANNOT_SUPPORT) {
                out[j][i][0] = 255;
            }
        }
    }
}


void next_slice(const int ni, const int nj,
                const float pixels_per_mm,
                const float support_offset,
                uint8_t const*const*const prev,
                uint8_t* const*const curr)
{
    float** const d = malloc(nj*sizeof(float*));
    for (int j=0; j < nj; ++j)  d[j] = malloc(ni*sizeof(float));

    distance_transform(ni, nj, pixels_per_mm, prev, d);


    for (int j=0; j < nj; ++j) {
        for (int i=0; i < ni; ++i) {
            if (curr[j][i] || d[j][i] < support_offset)
                curr[j][i] = FILLED;
            else if (prev[j][i] == BLOCKED || prev[j][i] == FILLED)
                curr[j][i] = BLOCKED;
        }
    }

    for (int j=0; j < nj; ++j)  free(d[j]);
    free(d);
}
