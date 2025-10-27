/*
ID: sumanm
LANG: C++
TASK: crypt1
*/
#include <iostream>
#include <fstream>
#include <string.h>
#include <vector>

using namespace std;

int main()
{
    ofstream fout ("crypt1.out");
    ifstream fin ("crypt1.in");

    vector<int> nums;
    int n;
    fin>>n;

    for(int i = 0; i < n; i++)
    {
        int x;
        fin>>x;
        nums.push_back(x);
    }

    
}