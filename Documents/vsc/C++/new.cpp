#include <iostream>
#include <fstream>
#include <string.h>
#include <vector>
#include <utility>
#include <algorithm>

using namespace std;

int main()
{
    ofstream fout("");
    ifstream fin("transform.in");

    vector<vector<char> > temp;
    for(int i = 0; i < 5; i++)
    {
        vector<char> t;
        temp.push_back(t);
        string in;
        fin>>in;
        for(int j = 0; j < 5; j++)
        {
            temp[i].push_back(in[j]);
        }
    }
    int n = temp.size();
    for(int j = 0; j < n; j++)
    {
        for(int k = 0; k < n; k++)
        {
            cout<<temp[j][k]<<" ";
        }
        cout<<"\n";
    }
    cout<<endl;
    for(int i = 0; i < n/2; i++)
    {
        for(int j = 0; j < n; j++)
        {
            int t = temp[i][j];
            temp[i][j] = temp[temp.size()-i-1][j];
            temp[temp.size()-i-1][j] = t;
        }
    }
    for(int j = 0; j < n; j++)
    {
        for(int k = 0; k < n; k++)
        {
            cout<<temp[j][k]<<" ";
        }
        cout<<"\n";
    }
}