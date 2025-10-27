/*
ID: sumanm
LANG: C++
TASK: milk2
*/
#include <iostream>
#include <fstream>
#include <string.h>
#include <vector>
#include <utility>
#include <algorithm>

using namespace std;

int main()
{
     ofstream fout ("milk2.out");
    ifstream fin ("milk2.in");

    int n;
    fin>>n;

    
}


/*
using point = pair<int, int>;
vector<point> P;
int main()
{
    ofstream fout ("milk2.out");
    ifstream fin ("milk2.in");

    int n;
    fin>>n;

    for(int i = 0; i < n; i++)
    {
        int first;
        int sec;
        fin>>first>>sec;
        P.push_back(make_pair(first, -1));
        P.push_back(make_pair(sec, 1));
    }
    sort(P.begin(), P.end());
    int farmers = 0, curMax = 0, curIdle = 0, finMax = 0, finIdle = 0;
    for(int i = 0; i < P.size(); i++)
    {
        if(i != 0)
        {
            if(farmers)
            {
                curMax += P[i].first - P[i - 1].first;
                curIdle = 0;
                finMax = max(curMax, finMax);
            }
            else
            {
                curIdle += P[i].first - P[i - 1].first;
                curMax = 0;
                finIdle = max(curIdle, finIdle);
            }
        }
        if(P[i].second == -1)
        {
            farmers++;
        }
        else
        {
            farmers--;
        }
    }
    fout<<finMax<<" "<<finIdle<<"\n";
}*/
