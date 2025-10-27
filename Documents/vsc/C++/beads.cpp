/*
ID: sumanm
LANG: C++
TASK: beads
*/
#include <iostream>
#include <fstream>
#include <string.h>
#include <algorithm>

using namespace std;

int main()
{
    ofstream fout ("beads.out");
    ifstream fin ("beads.in");

    bool con = true;
    int n, maxOf;
    string nlace;
    fin>>n>>nlace;

    int r = 0;
    int b = 0;
    int w = 0;
    int rMax = 0;
    int bMax = 0;
    nlace = nlace+nlace;
    int size = nlace.size();
    string semp;
    for(int i = n - 1; i >= 0; i--)
    {
        semp += nlace[i];
    }
    if(semp==nlace.substr(0, nlace.size()/2))
    {
        con = false;
        maxOf = n;   
    }
    if(con)
    {
        for(int i = 0; i < n; i++)
        {
            int j = i;
            char c = nlace[i];

            if(c == 'w')
            {
                w++;
            }
            else if(c == 'r')
            {
                int temp;
                while(nlace[j] != 'b' && j<size)
                {
                    r++;
                    j++;
                }
                r+=w;
                temp = j;
                while(nlace[temp] == 'w')
                {
                    temp--;
                }
                while(nlace[j]!= 'r' && j<size)
                {
                    b++;
                    j++;
                }
                maxOf = max(r+b, maxOf);
                i = temp;
                w=0;
                r = 0;
                b = 0;
            }
            else if(c=='b')
            {
                int temp;
                while(nlace[j] != 'r' && j<size)
                {
                    b++;
                    j++;
                }
                b+=w;
                temp = j;
                while(nlace[temp] == 'w')
                {
                    temp--;
                }
                while(nlace[j]!= 'b' && j<size)
                {
                    r++;
                    j++;
                }
                maxOf = max(r+b, maxOf);
                i = temp;
                w=0;
                r = 0;
                b = 0;
            }
        }
    }
    fout<<maxOf<<endl;
    exit(0);
}
