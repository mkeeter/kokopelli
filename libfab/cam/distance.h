#ifndef DISTANCE_H
#define DISTANCE_H

#include <stdint.h>

/** @brief Computes the Euclidean distance transform of the input image.
    @details Non-zero parts of the input image are considered filled.
    Output values in the distance array are in mm, scaled based on the
    pixels_per_mm input argument.

    @param ni Image width
    @param nj Image height
    @param pixels_per_mm Image scale
    @param img Image lattice
    @param distances Output lattice
*/
void distance_transform(const int ni, const int nj,
                        const float pixels_per_mm,
                        uint8_t const*const*const img, // Input
                        float* const*const distances);  // Output


/** @brief Performs the first stage of the Meijster distance transform.
    @details Non-zero parts of the input image are considered filled.

    @param imin Start of region to process (column number)
    @param imax End of region (column number)
    @param ni Image width
    @param nj Image height
    @param img Image lattice
    @param g Output lattice (minimum vertical distance)
*/
void distance_transform1(const int imin, const int imax,
                         const int ni, const int nj,
                         uint8_t const*const*const img, int32_t** const g);

/** @brief Performs the second stage of the Meijster distance transform.
    @details Output values in the distances array are in mm, scaled based on the
    pixels_per_mm input argument.

    @param jmin Start of region to process (row number)
    @param jmax End of region (row number)
    @param ni Image width
    @param nj Image height
    @param pixels_per_mm Image scale
    @param g Input G lattice (from first stage of transform)
    @param distances Output lattice
*/
void distance_transform2(const int jmin, const int jmax,
                         const int ni, const float pixels_per_mm,
                         int32_t** const g,
                         float* const*const distances);


/** @brief Euclidean distance evaluation function
    @details See Meijster's 2000 paper for details.
*/
unsigned f_edt(const int x, const int i, const int*const g);


/** @brief Euclidean distance separator
    @details See Meijster's 2000 paper for details.
*/
unsigned sep_edt(const int i, const int u, const int*const g);

#endif
