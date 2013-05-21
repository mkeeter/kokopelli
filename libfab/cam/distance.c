#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>

#include "cam/distance.h"

// Euclidean distance evaluation function
unsigned f_edt(const int x, const int i, const int32_t*const g)
{
    return (x-i)*(x-i) + g[i]*g[i];
}


// Euclidean distance separator function
unsigned sep_edt(const int i, const int u, const int32_t*const g)
{
    return (u*u - i*i + g[u]*g[u] - g[i]*g[i]) / (2*(u-i));
}


void distance_transform1(const int imin, const int imax,
                         const int ni, const int nj,
                         uint8_t const*const*const img, int32_t** const g)
{
//    printf("Running G on %i %i\n", imin, imax);
    for (int i=imin; i < imax; ++i) {
        g[0][i] = img[0][i] ? 0 : (ni+nj);

        // Sweep down
        for (int j=1; j < nj; ++j) {
            g[j][i] = img[j][i] ? 0 : (g[j-1][i]+1);
        }

        // Sweep up
        for (int j=nj-2; j >= 0; --j) {
            if (g[j+1][i] < g[j][i]) {
                g[j][i] = g[j+1][i]+1;
            }
        }
    }
//    printf("Done running G on %i %i\n", imin, imax);
}

void distance_transform2(const int jmin, const int jmax,
                         const int ni, const float pixels_per_mm,
                         int32_t** const g,
                         float* const*const distances)
{
//    printf("Running D on %i %i\n", jmin, jmax);

    // Starting points of each region
    unsigned t[ni];
    unsigned s[ni];

    for (int j=jmin; j < jmax; ++j) {
        int q=0; // Number of regions found so far
        s[0] = 0;
        t[0] = 0;
        for (int u=1; u < ni; ++u) {

            // Slide q backwards until we find a point where the
            // curve to be added is above the previous curve.
            while (q >= 0 && f_edt(t[q],s[q],g[j]) > f_edt(t[q],u,g[j])) {
                q--;
            }

            // If the new segment is below all previous curves,
            // then replace them all
            if (q < 0) {
                q = 0;
                s[0] = u;
            }

            // Otherwise, find the starting point for the new segment and
            // save it if it's within the bounds of the image.
            else {
                unsigned w = 1 + sep_edt(s[q], u, g[j]);
                if (w < ni) {
                    q++;
                    s[q] = u;
                    t[q] = w;
                }
            }
        }

        // Finally, calculate and store distance values.
        for (int u = ni-1; u >= 0; --u) {
            distances[j][u] = sqrt(f_edt(u, s[q], g[j])) / pixels_per_mm;
            if (u == t[q]) q--;
        }
    }
//    printf("Done running D on %i %i\n", jmin, jmax);
}


void distance_transform(const int ni, const int nj,
                        const float pixels_per_mm,
                        uint8_t const*const*const img, // Input
                        float* const*const distances)  // Output
{

    int** const g = malloc(nj*sizeof(int*));
    for (int j=0; j < nj; ++j)  g[j] = malloc(ni*sizeof(int));

    // Calculate g[j][i]
    for (int i=0; i < ni; ++i) {
        // Initialize the top point in this column
        g[0][i] = img[0][i] ? 0 : (ni+nj);

        // Sweep down
        for (int j=1; j < nj; ++j) {
            g[j][i] = img[j][i] ? 0 : (g[j-1][i]+1);
        }

        // Sweep up
        for (int j=nj-2; j >= 0; --j) {
            if (g[j+1][i] < g[j][i]) {
                g[j][i] = g[j+1][i]+1;
            }
        }
    }

    // Starting points of each region
    unsigned t[ni];
    unsigned s[ni];

    for (int j=0; j < nj; ++j) {
        int q=0; // Number of regions found so far
        s[0] = 0;
        t[0] = 0;
        for (int u=1; u < ni; ++u) {

            // Slide q backwards until we find a point where the
            // curve to be added is above the previous curve.
            while (q >= 0 && f_edt(t[q],s[q],g[j]) > f_edt(t[q],u,g[j])) {
                q--;
            }

            // If the new segment is below all previous curves,
            // then replace them all
            if (q < 0) {
                q = 0;
                s[0] = u;
            }

            // Otherwise, find the starting point for the new segment and
            // save it if it's within the bounds of the image.
            else {
                unsigned w = 1 + sep_edt(s[q], u, g[j]);
                if (w < ni) {
                    q++;
                    s[q] = u;
                    t[q] = w;
                }
            }
        }

        // Finally, calculate and store distance values.
        for (int u = ni-1; u >= 0; --u) {
            distances[j][u] = sqrt(f_edt(u, s[q], g[j])) / pixels_per_mm;
            if (u == t[q]) q--;
        }
    }

    for (int j=0; j < nj; ++j)  free(g[j]);
    free(g);
}
