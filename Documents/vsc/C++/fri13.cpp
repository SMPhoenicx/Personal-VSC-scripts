/*
ID: sumanm
LANG: C++
TASK: friday
*/
#include <iostream>
#include <fstream>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

using namespace std;


int month[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
int main()
{
    int day[] = {0,0,0,0,0,0,0};
    ofstream fout ("friday.out");
    ifstream fin ("friday.in");
    int n;
    fin>>n;
    int index = 0;
    for(int i = 1900; i < 1900+n; i++)
    {
        for(int j = 0; j < 12; j++)
        {
            day[index]++;
            cout<<"amt: "<<day[index]<<"\n";
            int leap = j == 1 && i % 4 == 0 && (i % 100 != 0 || i % 400 == 0);
            index = (index + month[j] + leap)%7;
        }
    }
    for(int i = 0; i < 6; i++) {
        fout << day[i] <<" ";
    }
    fout << day[6] << endl;
    exit(0);
}
