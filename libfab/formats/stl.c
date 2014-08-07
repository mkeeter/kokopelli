#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include <formats/stl.h>
#include <formats/mesh.h>

uint32_t read_int(FILE* file)
{
    struct {
        uint32_t i;
        char c;
    } ret;
    char * buf = fgets((char*)&ret, 5, file);
    return ret.i;
}

float read_float(FILE* file)
{
    struct {
        float f;
        char c;
    } ret;
    char * buf = fgets((char*)&ret, 5, file);
    return ret.f;
}

Mesh* load_stl(const char* filename)
{
    FILE* input = fopen(filename, "rb");

    Mesh* const mesh = calloc(1, sizeof(Mesh));
    mesh->X = (Interval){INFINITY, -INFINITY};
    mesh->Y = (Interval){INFINITY, -INFINITY};
    mesh->Z = (Interval){INFINITY, -INFINITY};

    // Skip the STL file header
    fseek(input, 80, SEEK_SET);
    // Read in the triangle count
    mesh->tcount = read_int(input);
    mesh->vcount = mesh->tcount * 3;

    // Allocate space for the incoming triangles and vertices
    mesh_reserve_t(mesh, mesh->tcount);
    mesh_reserve_v(mesh, mesh->vcount);

    for (int t=0; t < mesh->tcount; ++t) {
        // Current position in the vertex buffer
        // (each triangle is 3 vertices with 6 floats each)
        const unsigned v = t * 18;
        float normal[3];

        // First read the normal vector
        normal[0] = read_float(input);
        normal[1] = read_float(input);
        normal[2] = read_float(input);

        // Read 3 sets of 3 floats (each 4 bytes)
        for (int j=0; j < 18; j+=6) {
            float X = read_float(input);
            float Y = read_float(input);
            float Z = read_float(input);
            mesh->X.lower = fmin(mesh->X.lower, X);
            mesh->X.upper = fmax(mesh->X.upper, X);
            mesh->Y.lower = fmin(mesh->Y.lower, Y);
            mesh->Y.upper = fmax(mesh->Y.upper, Y);
            mesh->Z.lower = fmin(mesh->Z.lower, Z);
            mesh->Z.upper = fmax(mesh->Z.upper, Z);
            mesh->vdata[v+j] = X;
            mesh->vdata[v+1+j] = Y;
            mesh->vdata[v+2+j] = Z;
            mesh->vdata[v+3+j] = normal[0];
            mesh->vdata[v+4+j] = normal[1];
            mesh->vdata[v+5+j] = normal[2];
        }

        // Recompute the normal if it was not done in the file
        if (normal[0] == 0.0 && normal[1] == 0 && normal[2] == 0.0) {
            const float a1 = mesh->vdata[v+6] - mesh->vdata[v],
                        b1 = mesh->vdata[v+12] - mesh->vdata[v],
                        a2 = mesh->vdata[v+7] - mesh->vdata[v+1],
                        b2 = mesh->vdata[v+13] - mesh->vdata[v+1],
                        a3 = mesh->vdata[v+8] - mesh->vdata[v+2],
                        b3 = mesh->vdata[v+14] - mesh->vdata[v+2];

            // Get normal with cross product
            const float nx = a2*b3 - a3*b2,
                        ny = a3*b1 - a1*b3,
                        nz = a1*b2 - a2*b1;

            // And save the normal in the vertex buffer
            for (int i=0; i < 3; ++i) {
                mesh->vdata[v+3+i*6] = nx;
                mesh->vdata[v+4+i*6] = ny;
                mesh->vdata[v+5+i*6] = nz;
            }
        }

        // Ignore attribute byte count
        fseek(input, 2, SEEK_CUR);

        mesh->tdata[t*3]     = v;
        mesh->tdata[t*3 + 1] = v + 6;
        mesh->tdata[t*3 + 2] = v + 12;
    }

    fclose(input);

    return mesh;
}

////////////////////////////////////////////////////////////////////////////////

void save_stl(Mesh* mesh, const char* filename)
{
    FILE* stl = fopen(filename, "wb");

    // 80-character header
    fprintf(stl, "This is a binary STL file made in kokopelli    \n(github.com/mkeeter/kokopelli)\n\n");

    for (int i=0; i<4; ++i) {
        fputc(((char*)&mesh->tcount)[i], stl);
    }

    for (int t=0; t < mesh->tcount; ++t) {

        // Write the face normal (which we'll keep empty)
        for (int j=0; j < 12; ++j) fputc(0, stl);

        // Write out all of the vertices.
        for (int v=0; v < 3; ++v) {
            float xyz[3] = {
                mesh->vdata[6*mesh->tdata[t*3+v]],
                mesh->vdata[6*mesh->tdata[t*3+v]+1],
                mesh->vdata[6*mesh->tdata[t*3+v]+2]
            };
            for (int j=0; j < 12; ++j) {
                fputc(((char*)&xyz)[j], stl);
            }
        }

        fputc(0, stl);
        fputc(0, stl);
    }

    fclose(stl);
}

////////////////////////////////////////////////////////////////////////////////

/*
void draw_triangle(Triangle tri, Region r, uint16_t*const*const img)
{
    int imin = ni*(fmin(fmin(tri.x0, tri.x1), tri.x2) - xmin) / (xmax - xmin);
    if (imin < 0)   imin = 0;

    int imax = ni*(fmax(fmax(tri.x0, tri.x1), tri.x2) - xmin) / (xmax - xmin);
    if (imax >= ni)   imax = ni-1;

    int jmin = nj*(fmin(fmin(tri.y0, tri.y1), tri.y2) - ymin) / (ymax - ymin);
    if (jmin < 0)   jmin = 0;

    int jmax = nj*(fmax(fmax(tri.y0, tri.y1), tri.y2) - ymin) / (ymax - ymin);
    if (jmax >= nj)   jmax = 0;
}
*/
