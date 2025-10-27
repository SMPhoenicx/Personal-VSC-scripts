/*
ID: sumanm
LANG: C++
TASK: milk
*/
#include <iostream>
#include <string>
#include <fstream>
#include <map>
using namespace std;

int main()
{ 
    ofstream fout ("milk.out");
    ifstream fin ("milk.in");

    int n, m;
    fin>>n>>m;
    int cost = 0;
    map<int, int> mp;

    for(int i = 0; i < m; i++)
    {
        int x, y;
        fin>>x>>y;
        if(mp.find(x) == mp.end()) mp.insert(pair<int, int>(x, y));
        else mp[x] += y;
    }
    map<int, int>::iterator itr = mp.begin();
    while(n > 0 && itr != mp.end())
    {
        int x = itr->first;
        int y = itr->second;
        if(n >= mp[x])
        {
            n -= y;
            cost += x * y;
        }
        else
        {
            cost += n*x;
            n = 0;
        }
        itr++;
    }
    fout<<cost<<endl;
}