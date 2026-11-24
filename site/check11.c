//
// fastcode compo
//
//   verification/scoring program
// 
// LTP4. skal@planet-d.net
//////////////////////////////////////////////////////////////////
#include <stdio.h>

int Score = 0;
#define CHAR_SCORE         10
#define GRID_OUT_PENALTY  500
#define FALSE_SQUARE_PENALTY  5
#define LEFT_SQUARE         2

#define GW  16
#define GH  16
#define GridSize GW*GH


#define NB_CHARS 4      // <7
#define MAX_CLUSTER 4

//////////////////////////////////////////////////////////////////

typedef unsigned char       BYTE;
typedef short int           SHORT;
typedef unsigned short int  USHORT;

#define SHOW_ME_YOUR_SOUL

static BYTE Grid[GH][GW];
static BYTE GridBak[GH][GW];

int Nb_Blocks;
int step;

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


char *Grid0[16] = {
 "adbdcdbdddcbdbab",
 "bccbddbccaadcdaa",
 "dabdacdbbdacaccd",
 "cdababcacbdcadca",
 "baadababdddbaddb",  // <- this is an EXAMPLE!!!
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
 "dcddccdcccacdcdb"
};

void Use_Grid(char *G[GH]);

static int Vid_Ok = 0;
static int Use_Vid = 0;
void Print_Grid(BYTE Grid[GH][GW]);

void Loop();
int Get_Input();

void Error(char *s);

typedef struct {
        int val;
        int x;
        int y;

        }
position ;

position trajet[256];

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

//////////////////////////////////////////////////////////////////

#if 0
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
  usleep(200000);
}
#endif
//////////////////////////////////////////////////////////////////

void Remove(int j, int i)
{
#ifdef SHOW_ME_YOUR_SOUL
  Grid[j][i] = REMOVE_ME;
  //Show_Grid();
#endif
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

//////////////////////////////////////////////////////////////////

#define SWAP(a,b) { if (I[a]!=I[b]) { int n=R[a]; R[a]=R[b]; R[b]=n; I[b]=I[a]; } }


int Read_Hex(char c) {
  int j;
  if (c>='0' && c<='9') j = c-'0';
  else if (c>='a' && c<='f') j = 0x0a + c-'a';
  else if (c>='A' && c<='F') j = 0x0a + c-'A';
  else Error( "Invalid Hex in Read_Hex()\n" );
  return j;
}
/*
int Read_Line(char Buf[17]) {
  int i;
  int c;
gotoxy(1,20);
Redo:
  i = 0;
  while( (c=fgetc(stdin))!=EOF && c!='\n' && i<16)
    Buf[i++] = c;
  Buf[i] = 0;
  if (i==0) {
    fprintf( stderr, "unexpected EOF in Read_Line()\n" );
    goto Redo;
  }
  if (i!=2 && i!=16)
    Error( "Wrong input in Read_Line()\n" );
  return i;
}

void Read_Stop_Grid(char Buf[17])
{
  BYTE Cmp[GH][GW];
  int j, n, m;
  Line_To_Grid(Buf, Cmp[0]);
  for(j=1; j<16; ++j) {
    int i = Read_Line(Buf);
    Line_To_Grid(Buf, Cmp[j]);
  }

  for(n=m=j=0; j<GW*GH; ++j) {
    if (Grid[0][j]!=Cmp[0][j])
      n++;
    else if (Grid[0][j]!=0)
      m++;
  }
  printf( "Stop-Grid:\n" );
  Print_Grid(Cmp);
  printf( " ...should be:\n" );
  Print_Grid(Grid);
  Score += n*FALSE_SQUARE_PENALTY;
  Score += m*LEFT_SQUARE;
  printf( "-> Number of wrong characters: %d\n", n);
  printf( "-> Number of remaining characters: %d\n", m);
}


int Get_Input( int j, int i)
{
//  printf( "  Removed: (%d,%d)   ", i, j);
#ifdef SHOW_ME_YOUR_SOUL
  Grid[j][i] = REMOVE_ME;
  //Show_Grid();
#endif
  Grid[j][i] = 0;

  return 0;


 }
*/
 //////////////////////////////////////////////////////////////////
int Remove_Blocks() {
  int n=0, nb=0;
  do {
    Make_Fall();
    n = Remove_Clusters();
    nb += n;
  } while(n!=0);
  //printf(" %d",nb);
  return (nb);
}


int Remove_Clusters()
{
  int nb, i, R[GW*GH], I[GW*GH];
  BYTE *G = Grid[0];

  for( i=0; i<GW*GH; ++i ) I[i] = R[i] = i;
  for( i=0; i<GW*GH; ++i ) {
    if (G[i]==0) continue;
    if ( ((i%GW)!=GW-1) && (G[i+1]==G[i]) ) SWAP(i,i+1);
    if ( ((i/GW)!=GH-1) && (G[i+GW]==G[i])) SWAP(i,i+GW);
  }
  for( nb=i=0; i<GW*GH; ++i ) {
    int n, j;
    if (R[i]==-1) continue;
    n = 0;
    j = i;
    do { n++; i = R[i]; } while (i!=j);
    if (n>=MAX_CLUSTER) {
      nb += n;
      i=j;
      do { n=R[i]; R[i]=-1; G[i]=0; i=n; } while (i!=j);
    }
  }      
  return nb;
}

//////////////////////////////////////////////////////////////////
int result_tab[GH][GW];

position findmax (void)
{
position nbptr;

int px,py;
nbptr.val=0;

for (py=0;py<GH;py++) {
    for (px=0;px<GW;px++) {
    if (nbptr.val<=result_tab[px][py] ) {
       nbptr.val = result_tab[px][py];
       nbptr.x = px ;
       nbptr.y = py ;
       }
    }


}
return (nbptr) ;
}

char Calcule(void)
{
 int a,b;
 position where;
//on teste les 256 possibilit‚s
for (a=0; a<GH; a++)
{
   for (b=0; b<GW; b++) {
       memcpy (GridBak,Grid,GridSize);
       Remove(b,a);
       result_tab[b][a] = Remove_Blocks();
       memcpy (Grid,GridBak,GridSize);
   }
}

where=findmax();


Remove(where.x,where.y);
if (Remove_Blocks()==0) return 0;
//Show_Grid();

trajet[step].x=where.x;
trajet[step].y=where.y;
step++;
/*
        while(!kbhit());
        getchar();
*/
return 1;
}


void Loop()
{
int tabX,tabY;
  do {
      if (Calcule()==0) goto outloop;
  }
  while( Nb_Blocks>0 );

outloop:
        for (tabX=0;tabX<GW;tabX++)
            for (tabY=0;tabY<GH;tabY++)
                if (Grid[tabX][tabY]!=0) {
                trajet[step].x=tabX;
                trajet[step].y=tabY;
                step++;
                }


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


void Line_To_Grid(char Buf[17], BYTE *Grid)
{
  int i;
  for(i=0; i<GW; ++i) {
    char c = Buf[i];
    if (c!=' ' && (c<'a'||c>'d') ) {
      printf("Invalid grid character '%c'\n", Buf[i]);
      exit(1);
    }
    if (c==' ') Grid[i]=0;
    else Grid[i] = c-'a'+2;
  }
}

//////////////////////////////////////////////////////////////////

void Help()
{
  printf( "Options:\n" );
  printf( "-h :    help\n" );
  printf( "-vid :  show grid on display\n" );

  exit(0);
}
/*
void Parse_Args(int argc, char *argv[])
{
  int i;

  Use_Vid = 0;
  for(i=1; i<argc; ++i) {
    if (argv[i][0]=='-') {
      if (!strcmp(argv[i], "-vid"))
        Use_Vid = 1;
      else if (!strcmp(argv[i], "-h"))
        Help();
    }
  }
}
*/
typedef struct {
        int Stat;
        char chaine[256];
} key;

int main(int argc, char *argv[])
{
int pas;
char chainecle[256];
unsigned char Morceau=0;
int n,k,kgen;
int i,j;
int leng;
key keyclass[512];
if (argc < 2) {printf ("usage: %s xxxx, ex: %s abdd\n",argv[0]); exit(1);}
//  Parse_Args(argc, argv);
//  Grid0[70]="d";
  Use_Grid(Grid0);

for (leng=0;leng<4;leng++)
    Grid[4][leng+6]=Read_Hex(argv[1][leng])-8;
//  printf ("%d ",Read_Hex(argv[1][leng])-8);

/*
  for (i=0;i<16;i++) {
                     printf ("\n");
      for (j=0;j<16;j++) {
          printf ("%d ",Grid[i][j]); }

          }
*/
/*
printf ("%d", Grid[4][6]);
printf ("%d", Grid[4][7]);
printf ("%d", Grid[4][8]);
printf ("%d", Grid[4][9]);
*/
//  Show_Grid();
/*
        while(!kbhit());
        getchar();
*/
//        exit(1);


  printf( "Starting grid, with the missing line:\n" );
  //Print_Grid(Grid);
  step=0;
  Score=0;

//  if (Vid_Ok) Video_Off( );

//  printf( "Score=%d\n", Score);
//  printf ("%d etapes %d briques restant\n",step,Nb_Blocks);

k=0;

memcpy(GridBak,Grid,GridSize);

for (kgen=0;kgen<1;kgen++) {

n=0;

memcpy(Grid,GridBak,GridSize);

Loop();

for (pas=0;pas<step;pas++)
{

        if (trajet[pas].x<10) chainecle[n]=48+trajet[pas].x;
        else  chainecle[n]=55+trajet[pas].x;
        n++;

        if (trajet[pas].y<10) chainecle[n]=48+trajet[pas].y;
        else  chainecle[n]=55+trajet[pas].y;
        n++;
}

chainecle[n]=0;
//printf ("%s\n",chainecle);

//keyclass[k].Stat=step+Nb_Blocks;
keyclass[k].Stat=step;
strcpy (keyclass[k].chaine,chainecle);

printf ("stat : %d , %s\n", keyclass[k].Stat, keyclass[k].chaine);

k++;

}

return 0;
}

//////////////////////////////////////////////////////////////////
