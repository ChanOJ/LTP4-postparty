//
// LTP4- fastcode compo
//
// Initial-state search program
// - Explores the possible grids (search -s).
// - Finds a initial 4 squares  (search -g).
// 
//////////////////////////////////////////////////////////////////

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

typedef unsigned char       BYTE;
typedef short int           SHORT;
typedef unsigned short int  USHORT;

#define GW  16
#define GH  16
#define NB_CHARS 4      // <7
#define MAX_CLUSTER 4
#define LINE_J  4
#define LINE_I0  6
#define LINE_I1  10

//#define GW  4
//#define GH  4
//#define NB_CHARS 2
//#define MAX_CLUSTER 3

static BYTE Grid[GH][GW];

char *Grid0[16] = {
 "adbdcdbdddcbdbab",
 "bccbddbccaadcdaa",
 "dabdacdbbdacaccd",
 "cdababcacbdcadca",
 "baadabbddcdbaddb",
 "addbdaadcdaddcba",
 "adcacdabcabcaadc",
 "acadcbddbbcdcccd",
 "bdbaadaaabdcaaba",
 "adadbccbdacddcdb",
 "dbaaddbcbdbbbcaa",
 "dccbdcbaacaaacad",
 "cbdacbcadcbdddcc",
 "dbaadbacdcaaacab",
 "dbcdcdbadbbbdaca",
 "dcddccdcccacdcdb",
};


int Use_Grid0 = 0;
void Parse_Grid0();

//////////////////////////////////////////////////////////////////

static int CGrid[GH][GW];
int Nb_Blocks;

#define MAX_CHARS (2+NB_CHARS)
#define REMOVE_ME 1
static BYTE Grid_Chars[] = { ' ', 'O', 'a', 'b', 'c', 'd', 'e', 'f' };
#define BLK 8
#define LINE_COL 1
#define NB_COLS  (MAX_CHARS+1)
static BYTE Vid_Colors[] = { 
  0x00,0x00,0x00, // bckgrnd
  0xff,0xff,0xff, // lines
  0x80,0x80,0x80, // remove-me
  0xff,0x00,0x00, // chars...
  0x00,0x00,0xff,
  0x00,0xff,0x00,
  0x80,0x80,0x00,
  0x00,0x80,0x80,
  0xff,0x80,0x00
};
static BYTE Char_Colors[] = { 0, 2, 3, 4, 5, 6, 7, 8 };

//////////////////////////////////////////////////////////////////

static int Vid_Ok = 0;
static int Use_Vid = 0;
void Print_Grid(BYTE Grid[GH][GW]);
void Print_C_Grid(BYTE Grid[GH][GW]);
void Use_Grid(char *G[GH]);
void Make_Start_Grid();
void Search_Grid();
int Do_Search = 0;
int Do_Eval_Line = 1;
void Eval_Line();

void Error(char *s);

static BYTE Best_Grid[GH][GW] = {0};
int Best_Score=0;
int Evaluate_Grid(BYTE *Grid);

int Print_HTML = 0;
void Print_HTML_Grid(BYTE Grid[GH][GW]);
static char *Grid_HTML_Colors[] = { 
  "", "", 
  "#FF0000", "#00FF00",
  "#0000FF", "#FFFF00",
  "#330033", "#FF3300"
};

#define Width   (1+(BLK+1)*GW+15) // must be multiple of 8. Hence the '+15'...
#define Height  (1+(BLK+1)*GH+15)
#include "video.h"

//////////////////////////////////////////////////////////////////

void Error(char *s) {
  fprintf( stderr, "Error: %s", s);
  exit(1);
}

//////////////////////////////////////////////////////////////////

void Print_Grid(BYTE Grid[GH][GW])
{
  int i, j;
  fprintf( stderr, "+----------------+\n" );
  for(j=0; j<GH; ++j) {
    fprintf( stderr, "|" );
    for(i=0; i<GW; ++i) {
      fprintf( stderr, "%c", Grid_Chars[Grid[j][i]] );
    }
    fprintf( stderr, "|\n" );
  }
  fprintf( stderr, "+----------------+\n" );
}

void Print_C_Grid(BYTE Grid[GH][GW])
{
  int i, j;
  fprintf( stderr, "char *Grid[16] = {\n" );
  for(j=0; j<GH; ++j) {
    fprintf( stderr, " \"" );
    for(i=0; i<GW; ++i)
      fprintf( stderr, "%c", Grid_Chars[Grid[j][i]] );
    fprintf( stderr, "\",\n" );
  }
  fprintf( stderr, "};\n" );
}

void Print_HTML_Grid(BYTE Grid[GH][GW])
{
  int i, j;
  fprintf( stderr, "<table width=\"320\" height=\"320\" border=\"0\">\n");

  for(j=0; j<GH; ++j) {
    fprintf( stderr, " <tr>\n" );
    for(i=0; i<GW; ++i) {
      if (Print_HTML==2 && j==LINE_J && i>=LINE_I0 && i<LINE_I1)
      {
        fprintf( stderr, "  <td bgcolor=\"#FFFFFF\">&nbsp;</td>\n" );
      }
      else
        fprintf( stderr, "  <td bgcolor=\"%s\">&nbsp;</td>\n", Grid_HTML_Colors[Grid[j][i]] );
    }
    fprintf( stderr, "  <td bgcolor=\"#000000\">&nbsp;</td>\n" );
    fprintf( stderr, " </tr>\n" );
  }
  fprintf( stderr, "</table>\n");
}

//////////////////////////////////////////////////////////////////

void Show_Grid()
{
  int i, j, k;
  BYTE *Dst;
  if (!Use_Vid) return;
  if (Vid_Ok==0) {
    if (Video_On(256)) Error( "can't open video mode\n" );
    Video_Store_Colors(NB_COLS, Vid_Colors);
    Vid_Ok = 1;
  }

  Video_Lock();
  Dst = Vid_Mem;
  memset( Dst, LINE_COL, 1+(BLK+1)*GW);
  Dst += Stride;
  for(j=0; j<GH; ++j) {
    BYTE *Ptr = Dst;
    *Ptr++ = LINE_COL;
    for(i=0; i<GW; ++i) {
      BYTE Col = Char_Colors[Grid[j][i]];
      for(k=0; k<BLK; ++k) *Ptr++ = Col;
      *Ptr++ = LINE_COL;
    }
    for(k=1; k<BLK; ++k) {
      Dst += Stride;
      memcpy(Dst, Dst-Stride, Stride);
    }
    Dst += Stride;
    memset( Dst, LINE_COL, 1+(BLK+1)*GW);
    Dst += Stride;
  }
  Video_Unlock();
//  while(!Get_Key());
  usleep(10000);
}

//////////////////////////////////////////////////////////////////

void Remove_Random() {
  int i, j;
  i = (random()>>8)%GW;
  j = (random()>>8)%GH;
  Grid[j][i] = REMOVE_ME;
  Show_Grid();
  Grid[j][i] = 0;
}

void Make_Fall() {
  int i, j, k;
  Nb_Blocks = 0;
  for(i=0; i<GW; ++i) {
    k = GH-1;
    for(j=GH-1; j>=0; --j) {
      if (Grid[j][i]!=0) {
        Grid[k--][i] = Grid[j][i];
        Nb_Blocks++;
      }
    }
    for( ; k>=0; --k) Grid[k][i] = 0;
  }
}

#define SWAP(a,b) { if (I[a]!=I[b]) { I[b]=I[a]; n=R[a]; R[a]=R[b]; R[b]=n; } }
int Remove_Clusters()
{
  int nb, n;
  int i, j;
  int R[GW*GH], I[GW*GH];
  BYTE *G = Grid[0];

//  fprintf( stderr, "Before clusters:\n" ); Print_Grid(Grid);
  for( i=0; i<GW*GH; ++i ) I[i] = R[i] = i;

  for( i=0; i<GW*GH; ++i ) {
    if (G[i]==0) continue;
    if ( ((i%GW)!=GW-1) && (G[i+1]==G[i]) ) SWAP(i,i+1);
    if ( ((i/GW)!=GH-1) && (G[i+GW]==G[i])) SWAP(i,i+GW);

  }
  nb = 0;
  for( i=0; i<GW*GH; ++i ) {
    int n = 0;
    int j = i;
    if (R[i]==-1) continue;
    do { n++; i = R[i]; } while (i!=j);
    if (n>=MAX_CLUSTER) {
      nb += n;
//      fprintf( stderr, "Cluster of size %d starting at %d\n", n, j );
      i=j;
#if 1
      do { n=R[i]; R[i]=-1; G[i]=0; i=n; } while (i!=j);
#else
      do { n=R[i]; R[i]=-1; G[i]=REMOVE_ME; i=n; } while (i!=j);
      Show_Grid();
      for( j=0; j<GW*GH; ++j ) if (G[j]==REMOVE_ME) G[j]=0;        
#endif
    }
  }      
//  fprintf( stderr, "after clusters:\n" ); Print_Grid(Grid);
  return nb;
}

int Remove_Blocks() {
  int n=0, nb=0;
  do {
    Make_Fall();
    n = Remove_Clusters();
    nb += n;
  } while(n!=0);
  return nb;
}

//////////////////////////////////////////////////////////////////

void Use_Grid(char *G[GH])
{
  int i, j, k;
  for(j=0; j<GH; ++j) {
    for(i=0; i<GW; ++i) {
      char c=G[j][i];
      for(k=sizeof(Grid_Chars)-1; k>=0; --k)
        if (c==Grid_Chars[k])
          break;
      if (k<0)
        Error("Unknown character given in grid.\n");
      Grid[j][i] = k;
    }
  }
}

void Parse_Grid0()
{
  int i, j;
  for(j=0; j<GH; ++j) {
    for(i=0; i<GW; ++i) {
      int c = fgetc(stdin);
      if (c==EOF)
        Error( "EOF while reading stdin.\n" );
      Grid0[j][i] = (char)c;
    }
    if (fgetc(stdin)!='\n')
      Error("Extraneous chars in Parse_Grid0()\n");
  }
}

void Make_Start_Grid()
{
  int i, j;
  srandom(265);
  for(j=0; j<GH; ++j) {
    for(i=0; i<GW; ++i) {
      Grid[j][i] = 2+((random()>>8)%NB_CHARS);
    }
  }
}

//////////////////////////////////////////////////////////////////////////////////////////////
int Pos = 0;
int Rand_Ordering[NB_CHARS*2];
int Rand_W_Ordering[GW];
//////////////////////////////////////////////////////////////////////////////////////////////

int Evaluate_Grid(BYTE *LGrid)
{
  BYTE Save_Grid[GW*GH];
  int i, j, Ok;
  int Score;

  Score = 0;
  Ok = 0;
  memcpy(Save_Grid, LGrid, GW*GH);

  for(i=GH*GW-1; i>=GW; --i) {
    memcpy(Grid, Save_Grid, GW*GH);
    Grid[0][i] = 0;
    Score += Remove_Blocks();
    if (Score>=Best_Score) break;
  }
  if (Score<Best_Score) {
    memcpy(Best_Grid, Save_Grid, GW*GH);
    Best_Score = Score;
    Ok = 1;
  }

  memcpy(LGrid, Save_Grid, GW*GH);
  return Ok;
}

//////////////////////////////////////////////////////////////////////////////////////////////

static int Safe_Test(BYTE Grid[GW][GH]) {
  int n;
  BYTE Save_Grid[GW*GH];
  memcpy(Save_Grid, Grid, GW*GH);
  n = Remove_Clusters();
  memcpy(Grid, Save_Grid, GW*GH);
  return n;
}

static void Mix_Line(BYTE Grid[GW][GH])
{
  int b, k;

  b = random()%NB_CHARS;
  for(k=0; k<NB_CHARS; ++k)
  {
    Grid[LINE_J][Pos] = Rand_Ordering[b+k];
    Show_Grid();

//    if (Safe_Test(Grid)) continue;
//    fprintf( stderr, "Pos=%d\n", Pos );
    if (Pos!=LINE_I1-1) {
      Pos++;
      Mix_Line(Grid);
      Pos--;
    }
    else {
      int n;
      
      n = Safe_Test(Grid);
      if (n==0) {
        fprintf( stderr, "#%d -> Line[%d][%d-%d] = ", Best_Score, LINE_J, LINE_I0, LINE_I1);
        for(n=LINE_I0; n<LINE_I1; ++n)
          fprintf( stderr, "%c", Grid_Chars[Grid[LINE_J][n]] );
        fprintf( stderr, "\n" );
        Best_Score++;
      }
      else {
        static int Cnt=0;
        static int All_n = 0;
        static int N=0;
        N++;
        All_n += n;
        if (++Cnt==200000) {
          Show_Grid();
          printf( "#%d: mean n=%.3f\n", N, 1.0f*All_n/N);
          Cnt=0;
        }
      }
    }
  }
}

void Eval_Line()
{
  int k;
  for(k=0; k<NB_CHARS;++k)
    Rand_Ordering[k] = Rand_Ordering[k+NB_CHARS] = k+2;
#if 0
  for(k=0; k<GW;++k) Rand_W_Ordering[k] = k;
  for(k=0; k<GW*4; ++k) {
    int i, j, t;
    i = random()%GW;
    j = random()%GW;
    t = Rand_W_Ordering[i];
    Rand_W_Ordering[i] =  Rand_W_Ordering[j];
    Rand_W_Ordering[j] = t;
  }
#endif

  Best_Score = 0;
  Pos = LINE_I0;
  Mix_Line(Grid);
  fprintf( stderr, "Eval_Line: Number of possible lines=%d\n", Best_Score);
}

//////////////////////////////////////////////////////////////////

int Search(BYTE* LGrid)
{
  int k, b;
  static int Grid_Nb=0, Cnt = 0;

  b = random()%NB_CHARS;

  for(k=0; k<NB_CHARS; ++k) {
    LGrid[Pos] = Rand_Ordering[b+k];
    memcpy( Grid, LGrid, GW*GH );
    Grid_Nb++;
    if (++Cnt==50000) {
      Cnt=0;
      fprintf( stdout, "Grid #%d Pos=%d, k=%=%d\n", Grid_Nb, Pos, Rand_Ordering[b+k]);
      Show_Grid();
    }
    if (Remove_Blocks()!=0) continue;
    if (Pos==0) {
      if (Evaluate_Grid(LGrid)) {
        fprintf(stderr, "Score:%d\n", Best_Score);
        Print_C_Grid(Best_Grid);
        Show_Grid();
      }        
      return 0;
    }
    Pos--;
    if (Search(LGrid))
      return 1;
    Pos++;
  }
  LGrid[Pos] = 0;
  return 0;
}

void Search_Grid() {
  int i;
  BYTE LGrid[GH*GW];

  Best_Score=10000000;
  for(i=0; i<NB_CHARS;++i)
    Rand_Ordering[i] = Rand_Ordering[i+NB_CHARS] = i+2;
  for(i=0; i<GH*GW;++i) LGrid[i] = 0;
  Pos = GW*GH-1;
  Search(LGrid);
}

//////////////////////////////////////////////////////////////////

void Loop() {
  do {
    int n;
    Remove_Random();
    n = Remove_Blocks();
    Show_Grid();
    printf( "Nb_Blocks=%d Removed:%d\n", Nb_Blocks, n);
  }
  while( Nb_Blocks>0 );
}

//////////////////////////////////////////////////////////////////

void Help()
{
  printf( "Options:\n" );
  printf( "-h :     help\n" );
  printf( "-vid :   show grid on display\n" );
  printf( "-s :     search first grid\n" );
  printf( "-l :     Loop instead of evaluating the missing line\n" );
  printf( "-g :     start with grid0\n" );
  printf( "-html :  print grid0 in HTML\n" );
  printf( "-html2 : print grid0 in HTML with line removed\n" );
  exit(0);
}

void Parse_Args(int argc, char *argv[])
{
  int i;

  Use_Vid = 0;
  Do_Search = 0;
  Use_Grid0 = 0;
  Do_Eval_Line = 1;
  Print_HTML = 0;
  for(i=1; i<argc; ++i) {
    if (argv[i][0]=='-') {
      if (!strcmp(argv[i], "-vid"))
        Use_Vid = 1;
      else if (!strcmp(argv[i], "-s"))
        Do_Search = 1;
      else if (!strcmp(argv[i], "-l"))
        Do_Eval_Line = 0;
      else if (!strcmp(argv[i], "-g"))
        Use_Grid0 = 1;
      else if (!strcmp(argv[i], "-html"))
        Print_HTML = 1;
      else if (!strcmp(argv[i], "-html2"))
        Print_HTML = 2;
      else if (!strcmp(argv[i], "-h"))
        Help();
    }
  }
}

int main(int argc, char *argv[])
{
  Parse_Args(argc, argv);

  if (Do_Search) {
    Make_Start_Grid();
    Search_Grid();
  }
  else {
    if (!Use_Grid0) Parse_Grid0();
    Use_Grid(Grid0);
  }

  Print_C_Grid(Grid);
  if (Print_HTML) {
    Print_HTML_Grid(Grid);
    exit(0);
  }
    
  Show_Grid();

  if (Do_Eval_Line) {
    Eval_Line();
  }
  else Loop();
  if (Vid_Ok) Video_Off( );
  return 0;
}

//////////////////////////////////////////////////////////////////
