#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include <math.h>

#include "cam/toolpath.h"

#include "util/path.h"
#include "util/squares.h"

////////////////////////////////////////////////////////////////////////////////

/*  fill_ptrs
 *
 *  Fills the array ptrs with pointers to Path objects, which
 *  represent contours traced around the object.
 */
_STATIC_
void fill_ptrs(const int ni, const int nj,
               float const*const*const distances,
               const float mm_per_pixel, int num_contours,
               const float* const contour_levels,
               Path* (*const*const ptrs)[2]);

////////////////////////////////////////////////////////////////////////////////

int find_paths(const int ni, const int nj,
               float const*const*const distances,
               const float mm_per_pixel, const int num_contours,
               const float* const contour_levels,
               Path*** const paths)
{
    Path* (**const ptrs)[2] = malloc(nj*sizeof(Path*));
    for (int j=0; j < nj; ++j)  ptrs[j] = calloc(ni, sizeof(Path*)*2);

    // Figure out where the contours lie in this model
    fill_ptrs(ni, nj, distances, mm_per_pixel,
              num_contours, contour_levels, ptrs);

    // Allow one square pixel of decimation error
    float decimation_error = pow(mm_per_pixel/2, 2);

    *paths = malloc(sizeof(Path*));
    int allocated = 1;

    int path_count = 0;
    for (int j=0; j < nj; ++j) {
        for (int i=0; i < ni; ++i) {
            for (int e=0; e < 2; ++e) {
                Path* p = ptrs[j][i][e];
                if (!p) continue;

                // Grab this path and trace it out.
                Path* start = backtrace_path(p->prev, p);
                start = decimate_path(start, decimation_error);

                if (path_count >= allocated) {
                    allocated *= 2;
                    *paths = realloc(*paths, allocated*sizeof(Path*));
                }
                (*paths)[path_count++] = start;
                disconnect_path(start);
            }
        }
    }

    for (int j=0; j < nj; ++j)  free(ptrs[j]);
    free(ptrs);

    return path_count;
}

////////////////////////////////////////////////////////////////////////////////

_STATIC_
void fill_ptrs(const int ni, const int nj,
                      float const*const*const distances,
                      const float mm_per_pixel, int num_contours,
                      const float* const contour_levels,
                      Path* (*const*const ptrs)[2])
{
    for (int j=0; j < nj-1; ++j) {
        for (int i=0; i < ni-1; ++i) {

            int level;          // selected contour level
            uint8_t lookup = 0; // particular case for marching squares

            // Search up through the contour levels, halting when we either
            // find a contour that intersects this cell or we get out of range.
            for (level=0; level < num_contours; ++level) {
                lookup =
                    ((distances[j][i] <= contour_levels[level]) ? 1 : 0) |
                    ((distances[j+1][i] <= contour_levels[level]) ? 2 : 0) |
                    ((distances[j][i+1] <= contour_levels[level]) ? 4 : 0) |
                    ((distances[j+1][i+1] <= contour_levels[level]) ? 8 : 0);

                // If this cell is entirely below the given contour level,
                // then set d to "out of range" and break (since
                // contour_levels are in increasing order, we won't
                // ever find a contour in this cell).
                if (lookup == 0xf) {
                    level = num_contours;
                    break;
                }

                // Otherwise, we've found the appropriate level for this
                // cell, so we can go ahead and contour it!
                else if (lookup != 0) {
                    break;
                }
            }

            // If we didn't find a matching contour, then keep going
            if (level == num_contours)  continue;

            // Generate the (up to two) edges within this cell
            for (int e=0; e < 2; ++e) {
                // If this edge isn't defined, then skip it.
                if (EDGE_MAP[lookup][e][0] == -1)   continue;

                // Find the two points that make up this edge
                Path* prev = NULL;

                for (int pt=0; pt < 2; ++pt) {
                    // This ID is the edge on which one the current point lies
                    uint8_t id = EDGE_MAP[lookup][e][pt];

                    // Find the pointer to this edge in the global grid
                    Path** p   = &(ptrs[j + (id==1)][i + (id==3)][id/2]);

                    // If we haven't already created this point, then
                    // use interpolation to solve for the point's position
                    // on the selected edge of the cell.
                    if (!*p) {
                        // IDs of vertices
                        uint8_t v0 = VERTEX_MAP[id][0],
                                v1 = VERTEX_MAP[id][1];

                        // Lattice positions of vertices
                        int     j0 = j+(v0%2), i0 = i+(v0/2),
                                j1 = j+(v1%2), i1 = i+(v1/2);

                        // Distance samples at vertices
                        float   d0 = distances[j0][i0],
                                d1 = distances[j1][i1];

                        // Solve for interpolation == contour level
                        float   d  = (d0 - contour_levels[level]) / (d0 - d1);

                        *p  = calloc(1, sizeof(Path));
                        **p = (Path){
                            .x = mm_per_pixel*(i0+(i1-i0)*d+0.5),
                            .y = mm_per_pixel*(j0+(j1-j0)*d+0.5),
                            .ptrs = malloc(sizeof(Path**)),
                            .ptr_count = 1};
                        (**p).ptrs[0] = p;
                    }

                    // Link this point with the previous point
                    if (prev) {
                        prev->next = *p;
                        (*p)->prev = prev;
                    }
                    prev = *p;
                }
            }

        }
    }
}

////////////////////////////////////////////////////////////////////////////////




void sort_paths(Path const*const*const paths, const int num_paths,
                int* const order)
{
    // Bounds are stored in the order xmin, xmax, ymin, ymax
    float (*bounds)[4]    = malloc(num_paths*sizeof(float)*4);

    // Endpoints are (x,y) tuples
    float (*endpoints)[2] = malloc(num_paths*sizeof(float)*2);

    // Check every path, storing a bounding box and path endpoint
    for (int i=0; i < num_paths; ++i) {
        const Path* const start = paths[i];
        const Path* current = paths[i];
        bounds[i][0] = current->x;
        bounds[i][1] = current->x;
        bounds[i][2] = current->y;
        bounds[i][3] = current->y;
        do {
            if (current->x < bounds[i][0])  bounds[i][0] = current->x;
            if (current->x > bounds[i][1])  bounds[i][1] = current->x;
            if (current->y < bounds[i][2])  bounds[i][2] = current->y;
            if (current->y > bounds[i][3])  bounds[i][3] = current->y;
            endpoints[i][0] = current->x;
            endpoints[i][1] = current->y;
            current = current->next;
        } while (current != start && current != NULL);
    }



    // If before[i][j] is true, then path i needs to be cut before path j
    _Bool** before = malloc(num_paths*sizeof(_Bool*));
    for (int i=0; i < num_paths; ++i) {
        before[i] = malloc(num_paths*sizeof(_Bool));

        for (int j=0; j < num_paths; ++j) {
            if (i == j) {
                before[i][j] = false;
            }
            else if (bounds[i][0] >= bounds[j][0] &&
                     bounds[i][1] <= bounds[j][1] &&
                     bounds[i][2] >= bounds[j][2] &&
                     bounds[i][3] <= bounds[j][3])
            {
                before[i][j] = true;
            } else {
                before[i][j] = false;
            }
        }
    }

    float current_x = 0, current_y = 0;
    int current_path = 0;

    // Once a path is assigned an index, done is set to true
    _Bool* done = calloc(num_paths, sizeof(_Bool));

    while (current_path < num_paths) {

        // Find the min-distance path without anything before it.
        float best_distance = INFINITY;
        int best_path = 0;
        for (int i=0; i < num_paths; ++i) {
            if (done[i])    continue;

            // If there is anything before this path, then skip it
            _Bool valid = true;
            for (int j=0; j < num_paths; ++j) {
                if (before[j][i]) {
                    valid = false;
                    break;
                }
            }
            if (!valid) continue;

            float distance = pow(paths[i]->x - current_x, 2) +
                             pow(paths[i]->y - current_y, 2);
            if (distance < best_distance) {
                best_distance = distance;
                best_path = i;
            }
        }

        // Since we're selecting this path now, we can clear
        // all of the constraints that involve it.
        for (int j=0; j < num_paths; ++j)   before[best_path][j] = false;

        // Save the endpoint of this path as our current position
        current_x = endpoints[best_path][0];
        current_y = endpoints[best_path][1];

        // Mark that this path has been selected
        done[best_path] = true;

        order[current_path++] = best_path;
    }

    for (int i=0; i < num_paths; ++i)   free(before[i]);
    free(before);
    free(bounds);
    free(endpoints);
    free(done);
}

////////////////////////////////////////////////////////////////////////////////

_STATIC_
int make_flat_mill(const float diameter, const float mm_per_pixel,
                   const float mm_per_bit,
                   _Bool*** const mask, uint16_t*** const endmill)
{
    int d = diameter / mm_per_pixel;
    int r = d / 2;

    *mask = malloc(sizeof(_Bool*)*d);
    *endmill = malloc(sizeof(uint16_t*)*d);

    for (int j=0; j < d; ++j) {
        (*mask)[j] = calloc(d, sizeof(_Bool));
        (*endmill)[j] = calloc(d, sizeof(uint16_t));

        for (int i=0; i < d; ++i) {
            // Radius of this point (in mm units)
            const float p = sqrt( (i-r)*(i-r) + (j-r)*(j-r) ) * mm_per_pixel;

            // If we're within the mill bit's circle, mark it.
            if (p < diameter/2) {
                (*mask)[j][i] = true;
            }
        }
    }
    return d;
}

_STATIC_
int make_ball_mill(const float diameter, const float mm_per_pixel,
                   const float mm_per_bit,
                   _Bool*** const mask, uint16_t*** const endmill)
{
    int d = diameter / mm_per_pixel;
    int r = d / 2;

    *mask = malloc(sizeof(_Bool*)*d);
    *endmill = malloc(sizeof(uint16_t*)*d);

    for (int j=0; j < d; ++j) {
        (*mask)[j] = calloc(d, sizeof(_Bool));
        (*endmill)[j] = calloc(d, sizeof(uint16_t));

        for (int i=0; i < d; ++i) {
            // Radius of this point (in mm units)
            const float p = sqrt( (i-r)*(i-r) + (j-r)*(j-r) ) * mm_per_pixel;

            // If we're within the mill bit's circle, mark it.
            if (p < diameter/2) {
                (*mask)[j][i] = true;
                (*endmill)[j][i] = (diameter/2-
                                    (sqrt(diameter*diameter/4 - p*p)))
                                    /mm_per_bit;
            }
        }
    }
    return d;
}

_STATIC_
void free_endmill(_Bool** mask, uint16_t** endmill, int side)
{
    for (int i=0; i < side; ++i) {
        free(mask[i]);
        free(endmill[i]);
    }
    free(mask);
    free(endmill);
}


/*  get_max
 *
 *  Finds the highest point in a region defined by the mask and endmill
 *  arrays, centered on point i,j in a height-map of size ni by nj.
 */
_STATIC_
float get_max(const int i, const int j, const int ni, const int nj,
              const int side, const float mm_per_bit,
              uint16_t const*const*const heights,
              _Bool **const mask,
              uint16_t **const endmill)
{

    int max = 0;

    for (int b = j-side/2; b < j+side/2; ++b) {
        for (int a = i-side/2; a < i+side/2; ++a) {
            if (a < 0 || a >= ni || b < 0 || b >= nj)    continue;

            // Find positions within end-mill image
            int c = a-i+side/2, d = b-j+side/2;

            if (!mask[d][c])    continue;

            int height = heights[b][a] - endmill[d][c];

            if (height > max)    max = height;
        }
    }

    return max*mm_per_bit;
}


int finish_cut(const int ni, const int nj,
               uint16_t const*const*const heights,
               const float mm_per_pixel, const float mm_per_bit,
               const float diameter, const float overlap,
               const int mill_type, Path*** paths)
{

    _Bool** mask = NULL;
    uint16_t** endmill = NULL;
    int side = 0;
    if (mill_type == 0) {
        side = make_flat_mill(diameter, mm_per_pixel, mm_per_bit,
                              &mask, &endmill);
    } else if (mill_type == 1) {
        side = make_ball_mill(diameter, mm_per_pixel, mm_per_bit,
                              &mask, &endmill);
    } else {
        printf("Unknown end-mill type (expected 0 or 1, got %i)\n",
               mill_type);
    }

    int path_count = 0;

    // YZ cuts
    for (int i=(diameter/2)/mm_per_pixel; i < ni - (diameter/2)/mm_per_pixel;
             i += (diameter*overlap)/mm_per_pixel)
    {
        *paths = realloc(*paths, (++path_count)*sizeof(Path*));

        // Create a new path for each column
        Path*  prev    = NULL;
        Path** current = &(*paths)[path_count-1];

        // And fill it with points
        for (int j=0; j < nj; ++j) {
            float z = get_max(i, j, ni, nj, side, mm_per_bit,
                              heights, mask, endmill);

            *current = malloc(sizeof(Path));
            **current = (Path) {
                .prev=prev, .next=NULL,
                .x=i*mm_per_pixel, .y=j*mm_per_pixel, .z=z,
                .ptrs=NULL, .ptr_count=0
            };
            if (prev)   prev->next = *current;
            prev = *current;
            current = &((*current)->next);
        }
    }

    // XZ cuts
    for (int j=(diameter/2)/mm_per_pixel; j < nj - (diameter/2)/mm_per_pixel;
             j += (diameter*overlap)/mm_per_pixel)
    {
        *paths = realloc(*paths, (++path_count)*sizeof(Path*));
        Path* prev = NULL;
        Path** current = &(*paths)[path_count-1];

        for (int i=0; i < ni; ++i) {
            float z = get_max(i, j, ni, nj, side, mm_per_bit,
                              heights, mask, endmill);

            *current = malloc(sizeof(Path));
            **current = (Path) {
                .prev=prev, .next=NULL,
                .x=i*mm_per_pixel, .y=j*mm_per_pixel, .z=z,
                .ptrs=NULL, .ptr_count=0
            };
            if (prev)   prev->next = *current;
            prev = *current;
            current = &((*current)->next);
        }
    }

    free_endmill(mask, endmill, side);
    return path_count;
}
